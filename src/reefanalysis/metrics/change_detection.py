"""Depth change detection between two co-registered DEMs."""
from __future__ import annotations

import numpy as np

from ..dem import DEM


def dem_difference(t1: DEM, t2: DEM) -> np.ndarray:
    """t2 - t1 (positive = elevation gain / accretion). Grids must be identical."""
    if not t1.same_grid(t2):
        raise ValueError("DEMs must share extent, origin and resolution; grid both with common bounds")
    return t2.z - t1.z


def change_summary(diff: np.ndarray, res: float, lod: float = 0.15) -> dict:
    """Summarise change above the level of detection (LoD)."""
    valid = np.isfinite(diff)
    gain = valid & (diff > lod)
    loss = valid & (diff < -lod)
    cell = res**2
    return {
        "lod_m": lod,
        "valid_area_m2": float(valid.sum() * cell),
        "gain_area_m2": float(gain.sum() * cell),
        "loss_area_m2": float(loss.sum() * cell),
        "gain_volume_m3": float(diff[gain].sum() * cell),
        "loss_volume_m3": float(diff[loss].sum() * cell),
        "net_volume_m3": float((diff[gain].sum() + diff[loss].sum()) * cell),
        "mean_change_m": float(np.nanmean(diff)) if valid.any() else float("nan"),
        "pct_area_changed": float(100 * (gain | loss).sum() / max(valid.sum(), 1)),
    }
