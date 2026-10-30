"""Synthetic reef survey generator for samples and tests.

Creates a seafloor of sand with Gaussian "coral heads" plus noise, and a second survey (t2) where one
coral head has been removed (loss) and a new one has appeared (gain). Ground truth is therefore known.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# (x, y, height_m, radius_m)
HEADS_T1 = [(8, 8, 1.2, 2.0), (20, 10, 0.9, 1.6), (14, 22, 1.5, 2.5), (24, 24, 0.7, 1.4), (6, 24, 1.0, 1.8)]
HEADS_T2 = [h for h in HEADS_T1 if h[:2] != (20, 10)] + [(22, 18, 0.8, 1.5)]  # lose (20,10), gain (22,18)


def seafloor(x: np.ndarray, y: np.ndarray, heads) -> np.ndarray:
    z = -12.0 + 0.01 * x - 0.005 * y  # gentle slope
    for hx, hy, h, r in heads:
        z = z + h * np.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (2 * (r / 2) ** 2))
    return z


def make_survey(heads, extent: float = 30.0, spacing: float = 0.25, noise: float = 0.02,
                n_outliers: int = 30, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    g = np.arange(0, extent, spacing)
    xx, yy = np.meshgrid(g, g)
    x = xx.ravel() + rng.uniform(-spacing / 3, spacing / 3, xx.size)
    y = yy.ravel() + rng.uniform(-spacing / 3, spacing / 3, yy.size)
    z = seafloor(x, y, heads) + rng.normal(0, noise, x.size)
    cls = np.full(x.size, 40)  # ASPRS 40 = bathymetric point (seafloor)
    # sparse spurious returns (water column / noise)
    ox = rng.uniform(0, extent, n_outliers)
    oy = rng.uniform(0, extent, n_outliers)
    oz = rng.uniform(-9, -4, n_outliers)
    df = pd.DataFrame({"x": np.r_[x, ox], "y": np.r_[y, oy], "z": np.r_[z, oz], "class": np.r_[cls, np.full(n_outliers, 40)]})
    return df.round(3)


def write_samples(out_dir: str = "data/sample") -> tuple[str, str]:
    from pathlib import Path

    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    f1, f2 = p / "reef_survey_t1.csv", p / "reef_survey_t2.csv"
    make_survey(HEADS_T1, seed=1).to_csv(f1, index=False)
    make_survey(HEADS_T2, seed=2).to_csv(f2, index=False)
    return str(f1), str(f2)


if __name__ == "__main__":
    print(write_samples())
