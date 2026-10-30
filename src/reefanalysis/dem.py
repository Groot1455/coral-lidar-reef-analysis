"""Step 3 - DEM generation by binning points into a regular grid.

Convention: DEM.z[row, col]; row 0 is the southern edge (y = y0), col 0 is the western edge (x = x0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass
class DEM:
    z: np.ndarray
    x0: float
    y0: float
    resolution: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.z.shape

    def same_grid(self, other: "DEM") -> bool:
        return (
            self.shape == other.shape
            and np.isclose(self.x0, other.x0)
            and np.isclose(self.y0, other.y0)
            and np.isclose(self.resolution, other.resolution)
        )


def bounds_of(*clouds: np.ndarray) -> tuple[float, float, float, float]:
    allp = np.vstack([c[:, :2] for c in clouds])
    return float(allp[:, 0].min()), float(allp[:, 1].min()), float(allp[:, 0].max()), float(allp[:, 1].max())


def grid_points(
    points: np.ndarray,
    resolution: float,
    bounds: tuple[float, float, float, float] | None = None,
    method: str = "mean",
    max_fill_cells: int = 3,
) -> DEM:
    """Bin points into a DEM. method: mean | min | max. Empty cells are NaN unless filled."""
    if method not in ("mean", "min", "max"):
        raise ValueError("method must be mean, min or max")
    xmin, ymin, xmax, ymax = bounds or bounds_of(points)
    ncols = int(np.floor((xmax - xmin) / resolution)) + 1
    nrows = int(np.floor((ymax - ymin) / resolution)) + 1
    ix = np.floor((points[:, 0] - xmin) / resolution).astype(int)
    iy = np.floor((points[:, 1] - ymin) / resolution).astype(int)
    ok = (ix >= 0) & (ix < ncols) & (iy >= 0) & (iy < nrows)
    ix, iy, z = ix[ok], iy[ok], points[ok, 2]
    flat = iy * ncols + ix
    n = nrows * ncols
    if method == "mean":
        s = np.bincount(flat, weights=z, minlength=n)
        c = np.bincount(flat, minlength=n)
        with np.errstate(invalid="ignore", divide="ignore"):
            grid = np.where(c > 0, s / c, np.nan)
    elif method == "min":
        grid = np.full(n, np.inf)
        np.minimum.at(grid, flat, z)
        grid[np.isinf(grid)] = np.nan
    else:
        grid = np.full(n, -np.inf)
        np.maximum.at(grid, flat, z)
        grid[np.isinf(grid)] = np.nan
    dem = DEM(grid.reshape(nrows, ncols), xmin, ymin, resolution)
    if max_fill_cells > 0:
        dem.z = fill_gaps(dem.z, max_fill_cells)
    return dem


def fill_gaps(z: np.ndarray, max_cells: int) -> np.ndarray:
    """Nearest-neighbour fill of NaN cells that lie within max_cells of valid data."""
    mask = np.isnan(z)
    if not mask.any() or mask.all():
        return z
    dist, (ri, ci) = ndimage.distance_transform_edt(mask, return_indices=True)
    filled = z[ri, ci]
    out = z.copy()
    fillable = mask & (dist <= max_cells)
    out[fillable] = filled[fillable]
    return out
