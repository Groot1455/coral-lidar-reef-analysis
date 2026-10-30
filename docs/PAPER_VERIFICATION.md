# Base Paper Verification Checklist

The Chi Index is the primary method, but its definition has **not** been assumed anywhere in this repo. Fill in the sections below from the base paper, then implement `src/reefanalysis/metrics/chi_index.py`.

## Paper

- Title / authors / year / DOI:
- Study site and sensor (LiDAR platform, wavelength, point density):

## Chi Index definition

- [ ] Exact definition (in the paper's words, with page/equation number):
- [ ] Equation(s) and symbols:
- [ ] Inputs (DEM? point cloud? depth? slope? units?):
- [ ] Parameters (window size, resolution, thresholds) and recommended values:
- [ ] Output (per-cell map, per-reef scalar, class?):
- [ ] Interpretation (what high/low values mean; ecological claims actually supported):
- [ ] Stated advantages over rugosity and other methods (verify; do not copy unsupported claims):
- [ ] Validation data and results reported by the authors:
- [ ] Limitations stated by the authors:

## Implementation sign-off

- [ ] Worked numeric example from the paper reproduced as a test (replace the strict `xfail` test `test_chi_index_matches_paper` in `tests/test_pipeline.py`; the end-to-end test also asserts `not_implemented`, update it too)
- [ ] Results compared with the other four methods on the same dataset
- [ ] Reviewer:                      Date:
