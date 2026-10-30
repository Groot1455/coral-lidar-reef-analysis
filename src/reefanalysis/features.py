"""Step 4 - terrain feature extraction (slope, curvature, surface normals)."""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def nan_mean_filter(a: np.ndarray, size: int) -> np.ndarray:
    """Moving-window mean that ignores NaN cells."""
    valid = np.isfinite(a)
    s = ndimage.uniform_filter(np.where(valid, a, 0.0), size=size, mode="nearest")
    c = ndimage.uniform_filter(valid.astype(float), size=size, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = s / c
    out[c <= 1e-9] = np.nan
    return out


def gradients(z: np.ndarray, res: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (dz/dx, dz/dy). Columns are x, rows are y."""
    dzdy, dzdx = np.gradient(z, res)
    return dzdx, dzdy


def slope_deg(z: np.ndarray, res: float) -> np.ndarray:
    dzdx, dzdy = gradients(z, res)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def curvature(z: np.ndarray, res: float) -> np.ndarray:
    """Laplacian curvature (1/m). Positive = concave-up (pit), negative = convex (peak)."""
    zp = np.pad(z, 1, mode="edge")
    lap = (zp[2:, 1:-1] + zp[:-2, 1:-1] + zp[1:-1, 2:] + zp[1:-1, :-2] - 4 * z) / res**2
    return lap


def unit_normals(z: np.ndarray, res: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    dzdx, dzdy = gradients(z, res)
    norm = np.sqrt(dzdx**2 + dzdy**2 + 1.0)
    return -dzdx / norm, -dzdy / norm, 1.0 / norm
