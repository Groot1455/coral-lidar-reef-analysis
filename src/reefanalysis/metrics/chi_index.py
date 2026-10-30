"""Chi Index - PLACEHOLDER.

The Chi Index is the project's primary method, but its definition, formula and advantages MUST be taken
from the base research paper. This module intentionally does NOT guess a formula.

To implement:
  1. Fill in docs/PAPER_VERIFICATION.md (definition, inputs, equation, parameters, validation data).
  2. Implement `chi_index` below, matching the paper's equation and units.
  3. Replace the strict xfail test in tests/test_pipeline.py with a test against a worked example from the paper.
"""
from __future__ import annotations

import numpy as np


def chi_index(z: np.ndarray, res: float, **params) -> dict:
    """Compute the Chi Index per the base paper.

    Returns a dict (e.g. {"chi_map": ndarray, "chi_mean": float}) once implemented.
    """
    raise NotImplementedError(
        "Chi Index is not implemented: transcribe the definition from the base paper "
        "(see docs/PAPER_VERIFICATION.md) before enabling it."
    )
