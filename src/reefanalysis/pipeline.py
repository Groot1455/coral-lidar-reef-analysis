"""End-to-end pipeline orchestration (steps 1-7)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from .config import Config
from .dem import DEM, bounds_of, grid_points
from .features import curvature, slope_deg
from .io import load_points
from .metrics.change_detection import change_summary, dem_difference
from .metrics.chi_index import chi_index
from .metrics.complexity import complexity_summary, vector_ruggedness
from .metrics.obia import segment
from .metrics.rugosity import rugosity_map
from .metrics.reef_structure import reef_structure_summary, structural_complexity, vertical_relief
from .preprocess import filter_by_class, remove_statistical_outliers
from .visualize import plot_maps

log = logging.getLogger(__name__)


def _prep(path: str | Path, cfg: Config) -> np.ndarray:
    pts = load_points(path)
    n0 = len(pts)
    pts = filter_by_class(pts)
    pts = remove_statistical_outliers(pts, cfg.outlier_k, cfg.outlier_std)
    log.info("%s: %d -> %d points after preprocessing", Path(path).name, n0, len(pts))
    return pts


def run(input_path: str, compare_path: str | None = None, cfg: Config | None = None) -> dict:
    cfg = cfg or Config.from_env()
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    pts1 = _prep(input_path, cfg)
    pts2 = _prep(compare_path, cfg) if compare_path else None
    bounds = bounds_of(pts1, pts2) if pts2 is not None else bounds_of(pts1)

    dem1 = grid_points(pts1, cfg.dem_resolution, bounds, max_fill_cells=cfg.max_fill_cells)
    z, res = dem1.z, dem1.resolution

    sc_map = structural_complexity(z, cfg.window_cells)
    vr_map = vertical_relief(z, cfg.window_cells)

    results: dict = {
        "input": str(input_path),
        "dem_shape": list(z.shape),
        "dem_resolution_m": res,
        "n_points_used": int(len(pts1)),
        "complexity": complexity_summary(z, res, cfg.window_cells),
        "reef_structure": reef_structure_summary(sc_map, vr_map),
    }

    # Chi Index (primary method) - stays "not_implemented" until transcribed from the base paper
    try:
        chi = chi_index(z, res)
        results["chi_index"] = {"status": "ok", **{k: v for k, v in chi.items() if not isinstance(v, np.ndarray)}}
    except NotImplementedError as exc:
        results["chi_index"] = {"status": "not_implemented", "detail": str(exc)}

    rug = rugosity_map(z, res, cfg.window_cells)
    layers = {
        "DEM elevation (m)": z,
        "Slope (deg)": slope_deg(z, res),
        "Curvature (1/m)": curvature(z, res),
        "Local rugosity": rug,
        "Vector ruggedness": vector_ruggedness(z, res, cfg.window_cells),
        "Structural complexity (local SD, m)": sc_map,
        "Vertical relief (local range, m)": vr_map,
    }

    obia = segment(z, res, cfg.obia_classes, cfg.obia_min_cells, cfg.window_cells)
    results["obia"] = {"n_objects": obia["n_objects"], "classes": obia["class_stats"]}
    layers["OBIA class"] = np.where(obia["class_map"] < 0, np.nan, obia["class_map"])

    if pts2 is not None:
        dem2 = grid_points(pts2, cfg.dem_resolution, bounds, max_fill_cells=cfg.max_fill_cells)
        diff = dem_difference(dem1, dem2)
        results["change_detection"] = change_summary(diff, res, cfg.lod_m)
        layers["Elevation change (m)"] = diff
        np.save(out / "dem_change.npy", diff)

    np.save(out / "dem_t1.npy", z)
    np.save(out / "rugosity_map.npy", rug)
    np.save(out / "sc_map.npy", sc_map)
    np.save(out / "vr_map.npy", vr_map)
    fig = plot_maps(layers, out / "overview.png", res)
    results["figure"] = str(fig)

    with open(out / "metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log.info("Results written to %s", out)
    return results
