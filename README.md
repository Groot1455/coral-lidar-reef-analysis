# Coral Reef Health Analysis Using LiDAR Technology

A review-and-prototype project that compares methods for quantifying coral reef **structure** from LiDAR / bathymetric data, with the **Chi Index** (from our base paper) as the primary method.

> **Status:** the pipeline, four comparison methods, sample data and tests are working. The **Chi Index is a deliberate placeholder**: its definition must be transcribed from the base paper (see [`docs/PAPER_VERIFICATION.md`](docs/PAPER_VERIFICATION.md)) rather than assumed.

## Why

Coral reefs are threatened by warming, pollution and human activity. Diver-based surveys are slow and cover little area. Airborne/bathymetric LiDAR gives dense 3D data, from which reef morphology and structural complexity (a proxy for habitat quality, not a direct measure of coral health) can be derived.

## Methods compared

| Method | Module | Status |
|---|---|---|
| Chi Index (primary) | `metrics/chi_index.py` | Placeholder, pending base paper |
| Rugosity index (surface area / planar area) | `metrics/rugosity.py` | Implemented |
| OBIA (segmentation + classification) | `metrics/obia.py` | Implemented (simplified, KMeans + connected components) |
| Depth change detection | `metrics/change_detection.py` | Implemented |
| Structural complexity metrics (slope, curvature, TRI, VRM, fractal dimension) | `metrics/complexity.py` | Implemented |

## Quick start

```bash
git clone <your-repo-url> coral-lidar-reef-analysis
cd coral-lidar-reef-analysis

python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"              # add ",las" to read .las/.laz: pip install -e ".[dev,las]"

cp .env.example .env                 # optional; defaults work as-is

reefanalysis generate-sample         # (re)creates data/sample/*.csv
reefanalysis run \
  --input data/sample/reef_survey_t1.csv \
  --compare data/sample/reef_survey_t2.csv \
  --out outputs
pytest
```

Outputs in `outputs/`: `metrics.json`, `overview.png` (maps of DEM, slope, curvature, rugosity, VRM, SC, VR, OBIA classes and optional elevation change), and `.npy` rasters including `sc_map.npy` and `vr_map.npy`.

Without installing the package you can also run `PYTHONPATH=src python -m reefanalysis.cli run ...`.

## Dashboard

The GitHub Pages homepage is [`docs/index.html`](docs/index.html). It presents the **previously implemented health-class output** exactly as supplied: Poor 86.24%, Fair 2.84%, Good 10.92%, Excellent 0.00%. It includes summary cards and proportional charts. It is a static presentation of those existing numbers; it does not rerun the analysis or infer SC, VR, LCC, AC, or CHI values.

### Publish the dashboard on GitHub Pages

1. Commit and push the project with `docs/index.html` to the `main` branch.
2. On GitHub, open the repository and choose **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select branch **main** and folder **/docs**, then click **Save**.
5. GitHub Pages publishes the `docs/index.html` page as the site homepage.

For the existing repository `Groot1455/coral-health-index`, the expected site address is `https://groot1455.github.io/coral-health-index/`. GitHub's current publishing instructions are in the [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

The separate [`docs/dashboard/index.html`](docs/dashboard/index.html) is a pre-built synthetic pipeline example. The class-only page is also available at [`docs/dashboard/health.html`](docs/dashboard/health.html). Do not confuse the synthetic sample metrics with your previously implemented output.

### Combined reef health dashboard (structure + benthic indicators)

The pipeline calculates two local LiDAR structure metrics directly from the DEM:

- **SC (structural complexity):** moving-window standard deviation of elevation, in metres.
- **VR (vertical relief):** moving-window maximum minus minimum elevation, in metres.

Both ignore NoData cells and use the configured odd `REEF_WINDOW_CELLS` window. Their maps are saved as `outputs/sc_map.npy` and `outputs/vr_map.npy`; summary means and 95th percentiles are written to `metrics.json`. The dashboard also displays rugosity, slope, fractal dimension, OBIA and change-detection outputs.

**LCC and AC are not calculated from LiDAR elevation.** Supply percentages from your benthic classification in a JSON file. `chi_score` is optional and is treated as an externally calculated 0–1 score; the dashboard does not recompute it or claim the in-repository Chi Index is implemented.

Copy `data/sample/reef_indicators_template.json`, replace the `null` values with your measured results, and run:

```bash
reefanalysis dashboard --results outputs \
  --indicators data/my_reef_indicators.json \
  --out docs/dashboard/index.html
```

If your classification script prints class percentages like

```
Poor: 86.24%
Fair: 2.84%
Good: 10.92%
Excellent: 0.00%
```

save that output and add `--health health.txt`:

```bash
python your_script.py > health.txt
reefanalysis dashboard --results outputs \
  --health health.txt \
  --indicators data/my_reef_indicators.json \
  --out docs/dashboard/index.html
```

The class percentages are shown exactly as supplied, with a warning if they do not sum to roughly 100%. Accepted JSON keys for the indicator file are `site_name`, `survey_date`, `source`, `notes`, `lcc_percent`, `ac_percent`, and `chi_score`. Cover values must be 0–100; an external `chi_score` must be 0–1. Leave unavailable values as `null`. The page labels externally supplied values and does not calculate biological cover from LiDAR.

**Chi Index status:** `src/reefanalysis/metrics/chi_index.py` remains a placeholder until its equation is verified and transcribed from the base paper (see [`docs/PAPER_VERIFICATION.md`](docs/PAPER_VERIFICATION.md)). The dashboard displays that status instead of inventing a CHI formula.

## Environment variables

All optional (see [`.env.example`](.env.example)).

| Variable | Default | Meaning |
|---|---|---|
| `REEF_DATA_DIR` | `data/sample` | Input directory |
| `REEF_OUTPUT_DIR` | `outputs` | Results directory |
| `REEF_DEM_RESOLUTION` | `0.5` | DEM cell size (m) |
| `REEF_OUTLIER_K` | `8` | Neighbours for statistical outlier removal |
| `REEF_OUTLIER_STD` | `3.0` | Std-dev multiplier for outlier cutoff |
| `REEF_MAX_FILL_CELLS` | `3` | Max distance (cells) for nearest-neighbour gap fill |
| `REEF_WINDOW_CELLS` | `5` | Moving window for local rugosity/VRM (forced odd) |
| `REEF_LOD_M` | `0.15` | Level of detection for change detection (m) |
| `REEF_OBIA_CLASSES` | `4` | OBIA cluster count |
| `REEF_OBIA_MIN_CELLS` | `12` | Minimum OBIA object size (cells) |
| `REEF_LOG_LEVEL` | `INFO` | Logging level |

## Input formats

CSV with `x,y,z` (and optional `class`; ASPRS code 40 = bathymetric point is kept), `.npy` (N×3 or N×4), or `.las/.laz` (needs the `las` extra). Coordinates should be in a projected CRS in metres, and z in metres (negative below the surface).

## Repository layout

```
src/reefanalysis/   pipeline package (io, preprocess, dem, features, metrics/, pipeline, dashboard, cli)
data/sample/        synthetic two-survey dataset with known ground truth
tests/              unit + end-to-end tests
docs/               TECHNICAL_DESIGN.md, PAPER_VERIFICATION.md, dashboard/ (example)
```

## Sample data and test cases

`data/sample/` holds two synthetic 30 × 30 m surveys: coral heads on a gently sloping sand bed, plus noise and ~30 spurious returns. Between t1 and t2 one head is **removed** and one **added**, so change detection has known answers. Tests cover flat-surface rugosity = 1, 45° plane rugosity = √2, slope and curvature of planes, flat-surface fractal dimension = 2, SC/VR on flat and rough surfaces with NoData, gridding and gap filling, outlier removal, change volumes on a hand-built grid, dashboard inputs and an end-to-end run.

The sample data is synthetic, so metric values from it say nothing about real reefs.

## Limitations

- The Chi Index is not yet implemented (see above).
- OBIA class names are heuristic (ranked by rugosity) and unvalidated against field data.
- OBIA currently clusters on absolute elevation as well as slope and rugosity, so on sloping seabeds it can split flat areas by depth. Detrending the DEM first, or dropping elevation from the feature stack, is a likely improvement.
- Structural complexity is a proxy; it does not by itself establish ecological health.
- Change detection assumes the two surveys are co-registered; real data needs vertical/horizontal alignment and tide/water-level correction first.

## Next steps

1. Fill in `docs/PAPER_VERIFICATION.md` from the base paper and implement `chi_index`.
2. Add a real LiDAR/bathymetric dataset (keep large files out of git; `data/raw/` is ignored).
3. Compare Chi Index against rugosity/complexity on the same data.

## License

MIT, see [`LICENSE`](LICENSE).
