import numpy as np
import pytest

from reefanalysis.dem import DEM, fill_gaps, grid_points
from reefanalysis.features import curvature, slope_deg
from reefanalysis.metrics.change_detection import change_summary, dem_difference
from reefanalysis.metrics.complexity import fractal_dimension, vector_ruggedness
from reefanalysis.metrics.obia import segment
from reefanalysis.metrics.rugosity import rugosity_global, rugosity_map
from reefanalysis.metrics.reef_structure import structural_complexity, vertical_relief
from reefanalysis.preprocess import remove_statistical_outliers
from reefanalysis.sample_data import HEADS_T1, HEADS_T2, make_survey


def plane(slope_per_m: float, n=40, res=0.5):
    x = np.arange(n) * res
    return np.tile(x * slope_per_m, (n, 1)), res


def test_flat_surface_rugosity_is_one():
    z = np.zeros((30, 30))
    assert rugosity_global(z, 0.5) == pytest.approx(1.0)
    assert np.nanmin(rugosity_map(z, 0.5, 5)) == pytest.approx(1.0)


def test_45_degree_plane_rugosity_is_sqrt2():
    z, res = plane(1.0)
    assert rugosity_global(z, res) == pytest.approx(np.sqrt(2), rel=1e-6)


def test_slope_of_plane():
    z, res = plane(1.0)
    assert np.nanmean(slope_deg(z, res)) == pytest.approx(45.0, abs=1e-6)


def test_curvature_zero_on_plane_interior():
    z, res = plane(0.3)
    assert np.allclose(curvature(z, res)[2:-2, 2:-2], 0.0)


def test_fractal_dimension_flat_is_two():
    assert fractal_dimension(np.zeros((64, 64)), 0.5) == pytest.approx(2.0)


def test_rough_surface_has_higher_complexity_than_smooth():
    rng = np.random.default_rng(0)
    smooth = np.zeros((64, 64))
    rough = rng.normal(0, 0.2, (64, 64))
    assert rugosity_global(rough, 0.5) > rugosity_global(smooth, 0.5)
    assert np.nanmean(vector_ruggedness(rough, 0.5)) > np.nanmean(vector_ruggedness(smooth, 0.5))
    assert fractal_dimension(rough, 0.5) > 2.0


def test_grid_points_mean_and_gap_fill():
    pts = np.array([[0.1, 0.1, 1.0], [0.2, 0.2, 3.0], [2.6, 0.1, 5.0]])
    dem = grid_points(pts, 1.0, bounds=(0, 0, 2.5, 0.5), max_fill_cells=0)
    assert dem.z[0, 0] == pytest.approx(2.0)
    assert np.isnan(dem.z[0, 1])
    filled = fill_gaps(dem.z, 1)
    assert np.isfinite(filled[0, 1])


def test_outlier_removal_drops_isolated_point():
    rng = np.random.default_rng(1)
    pts = np.column_stack([rng.uniform(0, 5, 500), rng.uniform(0, 5, 500), rng.normal(0, 0.01, 500)])
    pts = np.vstack([pts, [2.5, 2.5, 50.0]])
    cleaned = remove_statistical_outliers(pts, k=8, std_ratio=3.0)
    assert len(cleaned) < len(pts)
    assert cleaned[:, 2].max() < 1.0


def test_change_detection_known_loss_and_gain():
    a = DEM(np.zeros((10, 10)), 0, 0, 1.0)
    z2 = np.zeros((10, 10))
    z2[0:2, 0:2] = 1.0   # gain: 4 m2 * 1 m = 4 m3
    z2[5:7, 5:8] = -0.5  # loss: 6 m2 * 0.5 m = 3 m3
    z2[9, 9] = 0.05      # below LoD
    b = DEM(z2, 0, 0, 1.0)
    s = change_summary(dem_difference(a, b), 1.0, lod=0.15)
    assert s["gain_volume_m3"] == pytest.approx(4.0)
    assert s["loss_volume_m3"] == pytest.approx(-3.0)
    assert s["gain_area_m2"] == pytest.approx(4.0)
    assert s["loss_area_m2"] == pytest.approx(6.0)


def test_change_detection_rejects_mismatched_grids():
    with pytest.raises(ValueError):
        dem_difference(DEM(np.zeros((5, 5)), 0, 0, 1.0), DEM(np.zeros((5, 5)), 1, 0, 1.0))


def test_obia_separates_bump_from_flat():
    z = np.zeros((60, 60))
    yy, xx = np.mgrid[0:60, 0:60]
    z += 1.5 * np.exp(-((xx - 30) ** 2 + (yy - 30) ** 2) / 50)
    out = segment(z, 0.5, n_classes=3, min_cells=5, window=5)
    assert out["class_map"].shape == z.shape
    assert out["n_objects"] >= 2
    assert out["class_map"][30, 30] != out["class_map"][2, 2]


def test_synthetic_pipeline_recovers_loss_and_gain():
    pts1 = make_survey(HEADS_T1, extent=30, spacing=0.25, n_outliers=0, seed=1).to_numpy()
    pts2 = make_survey(HEADS_T2, extent=30, spacing=0.25, n_outliers=0, seed=2).to_numpy()
    b = (0, 0, 30, 30)
    d1 = grid_points(pts1, 0.5, b)
    d2 = grid_points(pts2, 0.5, b)
    s = change_summary(dem_difference(d1, d2), 0.5, lod=0.15)
    assert s["loss_volume_m3"] < -0.5   # coral head at (20,10) removed
    assert s["gain_volume_m3"] > 0.3    # new head at (22,18)


def test_sc_and_vr_are_zero_on_flat_surface():
    z = np.full((15, 15), -2.0)
    assert np.nanmax(structural_complexity(z, 5)) == pytest.approx(0.0)
    assert np.nanmax(vertical_relief(z, 5)) == pytest.approx(0.0)


def test_sc_and_vr_detect_local_reef_relief_and_ignore_nodata():
    z = np.zeros((15, 15), dtype=float)
    z[7, 7] = 2.0
    z[0:5, 0:5] = np.nan
    sc = structural_complexity(z, 5)
    vr = vertical_relief(z, 5)
    assert sc.shape == z.shape and vr.shape == z.shape
    assert np.isnan(sc[1, 1]) and np.isnan(vr[1, 1])
    assert np.isnan(sc[4, 4]) and np.isnan(vr[4, 4])  # preserve the input NoData mask
    assert sc[7, 7] > 0
    assert vr[7, 7] == pytest.approx(2.0)
    assert np.isfinite(sc[7, 7]) and np.isfinite(vr[7, 7])


def test_sc_and_vr_reject_even_window():
    with pytest.raises(ValueError):
        structural_complexity(np.zeros((5, 5)), 4)
    with pytest.raises(ValueError):
        vertical_relief(np.zeros((5, 5)), 4)
