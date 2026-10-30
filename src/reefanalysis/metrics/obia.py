"""Object-Based Image Analysis (OBIA) on DEM-derived layers.

Simplified workflow: stack features -> standardise -> KMeans over cells -> connected-component objects ->
drop small objects. Class names are *heuristic* (ranked by mean rugosity) and are not field-validated.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from sklearn.cluster import KMeans

from ..features import slope_deg
from ..metrics.rugosity import rugosity_map

HEURISTIC_NAMES = {
    0: "flat / sand-rubble",
    1: "low relief",
    2: "moderate relief",
    3: "high relief / coral framework",
}


def segment(z: np.ndarray, res: float, n_classes: int = 4, min_cells: int = 12, window: int = 5, seed: int = 0) -> dict:
    layers = [z, slope_deg(z, res), rugosity_map(z, res, window)]
    valid = np.all([np.isfinite(l) for l in layers], axis=0)
    if valid.sum() < n_classes:
        raise ValueError("Not enough valid cells for OBIA")
    X = np.column_stack([l[valid] for l in layers])
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-12)
    km = KMeans(n_clusters=n_classes, n_init=10, random_state=seed).fit(X)

    # Order classes by mean rugosity so class 0 = smoothest
    rug = layers[2][valid]
    order = np.argsort([rug[km.labels_ == c].mean() for c in range(n_classes)])
    rank = np.empty(n_classes, dtype=int)
    rank[order] = np.arange(n_classes)
    class_map = np.full(z.shape, -1, dtype=int)
    class_map[valid] = rank[km.labels_]

    # Objects = connected components per class; small ones removed
    objects = np.zeros(z.shape, dtype=int)
    next_id = 1
    for c in range(n_classes):
        lab, n = ndimage.label(class_map == c)
        for i in range(1, n + 1):
            m = lab == i
            if m.sum() >= min_cells:
                objects[m] = next_id
                next_id += 1
    stats = []
    cell = res**2
    for c in range(n_classes):
        m = class_map == c
        stats.append(
            {
                "class": c,
                "heuristic_name": HEURISTIC_NAMES.get(c, f"class {c}"),
                "area_m2": float(m.sum() * cell),
                "pct_area": float(100 * m.sum() / max(valid.sum(), 1)),
            }
        )
    return {"class_map": class_map, "objects": objects, "n_objects": next_id - 1, "class_stats": stats}
