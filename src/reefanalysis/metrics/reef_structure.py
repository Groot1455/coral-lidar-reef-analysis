"""Local LiDAR-derived reef structure metrics (SC and VR).

SC is the moving-window standard deviation of elevation. VR is the moving-window
maximum minus minimum elevation. Both ignore non-finite/NoData cells.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _validate_window(window: int) -> int:
    if not isinstance(window, int) or window < 1:
        raise ValueError("window must be a positive integer")
    if window % 2 == 0:
        raise ValueError("window must be odd")
    return window


def structural_complexity(z: np.ndarray, window: int = 5) -> np.ndarray:
    """Return local elevation standard deviation (SC), in the DEM's elevation units."""
    window = _validate_window(window)
    a = np.asarray(z, dtype=float)
    valid = np.isfinite(a)
    # uniform_filter returns local means; dividing filtered sums by filtered
    # valid counts gives NoData-aware first and second moments.
    count = ndimage.uniform_filter(valid.astype(float), size=window, mode="nearest")
    values = np.where(valid, a, 0.0)
    mean = np.zeros_like(a, dtype=float)
    mean_sq = np.zeros_like(a, dtype=float)
    np.divide(
        ndimage.uniform_filter(values, size=window, mode="nearest"),
        count, out=mean, where=count > 0,
    )
    np.divide(
        ndimage.uniform_filter(values * values, size=window, mode="nearest"),
        count, out=mean_sq, where=count > 0,
    )
    variance = np.maximum(mean_sq - mean * mean, 0.0)
    out = np.sqrt(variance)
    out[(count <= 0) | (~valid)] = np.nan
    return out


def vertical_relief(z: np.ndarray, window: int = 5) -> np.ndarray:
    """Return local maximum-minus-minimum elevation (VR), in DEM elevation units."""
    window = _validate_window(window)
    a = np.asarray(z, dtype=float)
    valid = np.isfinite(a)
    count = ndimage.uniform_filter(valid.astype(float), size=window, mode="nearest")
    high = ndimage.maximum_filter(np.where(valid, a, -np.inf), size=window, mode="nearest")
    low = ndimage.minimum_filter(np.where(valid, a, np.inf), size=window, mode="nearest")
    out = high - low
    out[(count <= 0) | (~valid)] = np.nan
    return out


def reef_structure_summary(sc: np.ndarray, vr: np.ndarray) -> dict[str, float]:
    """Summarise SC and VR maps using means and 95th percentiles."""
    def stats(a: np.ndarray, prefix: str) -> dict[str, float]:
        values = np.asarray(a)[np.isfinite(a)]
        if values.size == 0:
            return {f"{prefix}_mean_m": float("nan"), f"{prefix}_p95_m": float("nan")}
        return {
            f"{prefix}_mean_m": float(np.mean(values)),
            f"{prefix}_p95_m": float(np.percentile(values, 95)),
        }

    return {**stats(sc, "SC"), **stats(vr, "VR")}
