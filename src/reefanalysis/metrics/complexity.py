"""Structural complexity metrics: slope/curvature statistics, TRI, VRM, fractal dimension."""
from __future__ import annotations

import numpy as np

from ..features import curvature, nan_mean_filter, slope_deg, unit_normals
from .rugosity import cell_surface_area, rugosity_global


def terrain_ruggedness(z: np.ndarray) -> np.ndarray:
    """Mean absolute elevation difference to the 8 neighbours (Wilson-style TRI)."""
    zp = np.pad(z, 1, mode="edge")
    diffs = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nb = zp[1 + dr : 1 + dr + z.shape[0], 1 + dc : 1 + dc + z.shape[1]]
            diffs.append(np.abs(nb - z))
    return np.mean(diffs, axis=0)


def vector_ruggedness(z: np.ndarray, res: float, window: int = 5) -> np.ndarray:
    """Sappington et al. VRM: 1 - |mean unit normal| within a window (0 = smooth, ->1 = rugged)."""
    nx, ny, nz = unit_normals(z, res)
    mx, my, mz = (nan_mean_filter(n, window) for n in (nx, ny, nz))
    return 1.0 - np.sqrt(mx**2 + my**2 + mz**2)


def fractal_dimension(z: np.ndarray, res: float, steps: tuple[int, ...] = (1, 2, 4, 8)) -> float:
    """Area-scale fractal dimension: surface area measured at coarsening scales.

    Relative area RA(s) = surface area / planimetric area ~ s^(2-D)  =>  D = 2 - slope of log RA vs log s.
    Flat surface -> RA = 1 at every scale -> D = 2.0.
    """
    logs, loga = [], []
    for k in steps:
        zk = z[::k, ::k]
        if min(zk.shape) < 3:
            continue
        area = cell_surface_area(zk, res * k)
        n_valid = np.isfinite(area).sum()
        if n_valid == 0:
            continue
        rel_area = np.nansum(area) / (n_valid * (res * k) ** 2)  # surface / planimetric area
        logs.append(np.log(res * k))
        loga.append(np.log(rel_area))
    if len(logs) < 2:
        return float("nan")
    slope = np.polyfit(logs, loga, 1)[0]
    return float(2.0 - slope)


def complexity_summary(z: np.ndarray, res: float, window: int = 5) -> dict:
    sl = slope_deg(z, res)
    cu = curvature(z, res)
    return {
        "rugosity_global": rugosity_global(z, res),
        "slope_mean_deg": float(np.nanmean(sl)),
        "slope_std_deg": float(np.nanstd(sl)),
        "curvature_std": float(np.nanstd(cu)),
        "tri_mean_m": float(np.nanmean(terrain_ruggedness(z))),
        "vrm_mean": float(np.nanmean(vector_ruggedness(z, res, window))),
        "fractal_dimension": fractal_dimension(z, res),
        "elevation_std_m": float(np.nanstd(z)),
    }
