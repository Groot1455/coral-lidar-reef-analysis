"""Step 7 - visualisation helpers (matplotlib, headless)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def plot_maps(layers: dict[str, np.ndarray], path: str | Path, res: float, ncols: int = 3) -> Path:
    """Plot named 2D layers as a panel figure. Row 0 (south) is drawn at the bottom."""
    n = len(layers)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.6 * ncols, 4 * nrows), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    for ax, (name, arr) in zip(axes.ravel(), layers.items()):
        ax.axis("on")
        extent = (0, arr.shape[1] * res, 0, arr.shape[0] * res)
        cmap = "RdBu" if "change" in name.lower() else ("tab10" if "class" in name.lower() else "viridis")
        im = ax.imshow(arr, origin="lower", extent=extent, cmap=cmap)
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
