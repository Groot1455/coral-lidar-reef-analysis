"""Rugosity index: ratio of 3D surface area to planimetric area (Jenness-style DEM surface ratio).

A perfectly flat surface gives 1.0; a plane inclined at 45 degrees gives sqrt(2).
"""
from __future__ import annotations

import numpy as np

from ..features import nan_mean_filter


def cell_surface_area(z: np.ndarray, res: float) -> np.ndarray:
    """3D surface area of each 2x2 block of grid posts (two triangles). Shape (rows-1, cols-1)."""
    z00, z01 = z[:-1, :-1], z[:-1, 1:]
    z10, z11 = z[1:, :-1], z[1:, 1:]
    r = res
    a1 = 0.5 * np.sqrt((r * (z01 - z00)) ** 2 + (r * (z10 - z00)) ** 2 + r**4)
    a2 = 0.5 * np.sqrt((r * (z10 - z11)) ** 2 + (r * (z01 - z11)) ** 2 + r**4)
    return a1 + a2


def rugosity_global(z: np.ndarray, res: float) -> float:
    area = cell_surface_area(z, res)
    valid = np.isfinite(area)
    if not valid.any():
        return float("nan")
    return float(area[valid].sum() / (valid.sum() * res**2))


def rugosity_map(z: np.ndarray, res: float, window: int = 5) -> np.ndarray:
    """Local rugosity: moving-window mean of per-cell surface ratio. Same shape as z."""
    ratio = cell_surface_area(z, res) / res**2
    padded = np.full(z.shape, np.nan)
    padded[:-1, :-1] = ratio
    return nan_mean_filter(padded, window)
