"""Step 2 - preprocessing: noise filtering and point classification."""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def remove_statistical_outliers(points: np.ndarray, k: int = 8, std_ratio: float = 3.0) -> np.ndarray:
    """Drop points whose mean distance to k nearest neighbours is > mean + std_ratio * std."""
    if len(points) <= k + 1:
        return points
    tree = cKDTree(points[:, :3])
    dist, _ = tree.query(points[:, :3], k=k + 1)
    mean_d = dist[:, 1:].mean(axis=1)
    thresh = mean_d.mean() + std_ratio * mean_d.std()
    return points[mean_d <= thresh]


def filter_by_class(points: np.ndarray, keep: tuple[int, ...] = (2, 12, 40, 41)) -> np.ndarray:
    """Keep ASPRS classes (default: ground, bathymetric seafloor 40, water surface excluded).

    If the cloud has no class column, it is returned unchanged.
    """
    if points.shape[1] < 4:
        return points
    return points[np.isin(points[:, 3].astype(int), keep)]


def clip_depth(points: np.ndarray, zmin: float | None = None, zmax: float | None = None) -> np.ndarray:
    z = points[:, 2]
    mask = np.ones(len(points), dtype=bool)
    if zmin is not None:
        mask &= z >= zmin
    if zmax is not None:
        mask &= z <= zmax
    return points[mask]
