"""Point cloud input. Supports CSV (x,y,z[,class]), .npy (N x 3 or N x 4) and .las/.laz (needs laspy)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_points(path: str | Path) -> np.ndarray:
    """Return an (N, 3) float array of x, y, z. A 4th column (class) is returned if present."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
        cols = [c for c in ("x", "y", "z") if c in df.columns]
        if len(cols) != 3:
            raise ValueError(f"{path} must have x,y,z columns; found {list(df.columns)}")
        if "class" in df.columns:
            cols.append("class")
        pts = df[cols].to_numpy(dtype=float)
    elif suffix == ".npy":
        pts = np.load(path).astype(float)
    elif suffix in (".las", ".laz"):
        try:
            import laspy
        except ImportError as exc:
            raise ImportError("Reading LAS/LAZ needs: pip install 'reefanalysis[las]'") from exc
        las = laspy.read(path)
        cols = [np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)]
        cols.append(np.asarray(las.classification, dtype=float))
        pts = np.column_stack(cols).astype(float)
    else:
        raise ValueError(f"Unsupported point cloud format: {suffix}")
    if pts.ndim != 2 or pts.shape[1] < 3:
        raise ValueError("Point array must be N x 3 (or N x 4)")
    pts = pts[np.all(np.isfinite(pts[:, :3]), axis=1)]
    return pts
