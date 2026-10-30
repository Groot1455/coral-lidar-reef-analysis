"""Runtime configuration, read from environment variables (optionally a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass
class Config:
    data_dir: str = "data/sample"
    output_dir: str = "outputs"
    dem_resolution: float = 0.5
    outlier_k: int = 8
    outlier_std: float = 3.0
    max_fill_cells: int = 3
    window_cells: int = 5
    lod_m: float = 0.15
    obia_classes: int = 4
    obia_min_cells: int = 12
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        win = _i("REEF_WINDOW_CELLS", 5)
        if win % 2 == 0:
            win += 1  # moving windows must be odd
        return cls(
            data_dir=os.environ.get("REEF_DATA_DIR", "data/sample"),
            output_dir=os.environ.get("REEF_OUTPUT_DIR", "outputs"),
            dem_resolution=_f("REEF_DEM_RESOLUTION", 0.5),
            outlier_k=_i("REEF_OUTLIER_K", 8),
            outlier_std=_f("REEF_OUTLIER_STD", 3.0),
            max_fill_cells=_i("REEF_MAX_FILL_CELLS", 3),
            window_cells=win,
            lod_m=_f("REEF_LOD_M", 0.15),
            obia_classes=_i("REEF_OBIA_CLASSES", 4),
            obia_min_cells=_i("REEF_OBIA_MIN_CELLS", 12),
            log_level=os.environ.get("REEF_LOG_LEVEL", "INFO"),
        )
