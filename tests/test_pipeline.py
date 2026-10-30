import json
import os

import pytest

from reefanalysis.cli import main
from reefanalysis.config import Config
from reefanalysis.io import load_points
from reefanalysis.metrics.chi_index import chi_index
from reefanalysis.pipeline import run


@pytest.fixture(scope="module")
def sample_files(tmp_path_factory):
    d = tmp_path_factory.mktemp("sample")
    assert main(["generate-sample", "--out", str(d)]) == 0
    return str(d / "reef_survey_t1.csv"), str(d / "reef_survey_t2.csv")


def test_load_points(sample_files):
    pts = load_points(sample_files[0])
    assert pts.shape[1] == 4 and len(pts) > 10000


def test_load_points_missing_file():
    with pytest.raises(FileNotFoundError):
        load_points("nope.csv")


def test_end_to_end(sample_files, tmp_path):
    cfg = Config(output_dir=str(tmp_path / "out"))
    res = run(sample_files[0], sample_files[1], cfg)
    assert (tmp_path / "out" / "metrics.json").exists()
    assert (tmp_path / "out" / "overview.png").exists()
    assert res["complexity"]["rugosity_global"] > 1.0
    assert res["reef_structure"]["SC_mean_m"] >= 0
    assert res["reef_structure"]["VR_mean_m"] >= 0
    assert (tmp_path / "out" / "sc_map.npy").exists()
    assert (tmp_path / "out" / "vr_map.npy").exists()
    assert res["change_detection"]["loss_volume_m3"] < 0 < res["change_detection"]["gain_volume_m3"]
    assert res["chi_index"]["status"] == "not_implemented"
    json.load(open(tmp_path / "out" / "metrics.json"))


@pytest.mark.xfail(raises=NotImplementedError, strict=True,
                   reason="Chi Index must be implemented from the base paper; replace with a worked-example test")
def test_chi_index_matches_paper():
    import numpy as np
    chi_index(np.zeros((10, 10)), 0.5)


def test_dashboard_builds(sample_files, tmp_path):
    cfg = Config(output_dir=str(tmp_path / "out"))
    run(sample_files[0], sample_files[1], cfg)
    assert main(["dashboard", "--results", str(tmp_path / "out")]) == 0
    page = (tmp_path / "out" / "dashboard.html").read_text()
    assert "Global rugosity" in page and "data:image/png;base64," in page
    assert "SC · local elevation SD" in page and "VR · local elevation range" in page
    assert "LCC · live coral cover" in page and "CHI · Chi Index" in page
    assert "Not implemented" in page


def test_health_dashboard_from_pasted_output(tmp_path):
    from reefanalysis.dashboard import parse_health

    f = tmp_path / "out.txt"
    f.write_text("...\nPoor: 86.24%\nFair: 2.84%\nGood: 10.92%\nExcellent: 0.00%\n>>>\n")
    h = parse_health(f)
    assert list(h) == ["Poor", "Fair", "Good", "Excellent"]
    assert h["Poor"] == pytest.approx(86.24)
    html_out = tmp_path / "h.html"
    assert main(["dashboard", "--health", str(f), "--out", str(html_out)]) == 0
    page = html_out.read_text()
    assert "86.24%" in page and "Largest share: <b>Poor</b>" in page and "not 100%" not in page


def test_health_parse_json_and_bad_sum_warning(tmp_path):
    from reefanalysis.dashboard import build_dashboard, parse_health

    f = tmp_path / "h.json"
    f.write_text('{"Good": 40, "Poor": 30}')
    h = parse_health(f)
    assert list(h) == ["Poor", "Good"]
    page = build_dashboard(None, tmp_path / "x.html", h).read_text()
    assert "not 100%" in page


def test_health_parse_rejects_garbage(tmp_path):
    from reefanalysis.dashboard import parse_health

    f = tmp_path / "g.txt"
    f.write_text("nothing useful here\n")
    with pytest.raises(ValueError):
        parse_health(f)


def test_dashboard_with_external_indicators(tmp_path):
    import json
    from reefanalysis.dashboard import parse_indicators, build_dashboard

    f = tmp_path / "indicators.json"
    f.write_text(json.dumps({
        "site_name": "Example Reef",
        "survey_date": "2026-10-30",
        "source": "Benthic classifier v1",
        "lcc_percent": 35.5,
        "ac_percent": 12.25,
        "chi_score": 0.72,
    }))
    indicators = parse_indicators(f)
    page = build_dashboard(None, tmp_path / "indicators.html", indicators=indicators).read_text()
    assert "Example Reef" in page and "35.500%" in page and "12.250%" in page
    assert "0.720 / 1.000" in page and "not recomputed here" in page


def test_indicator_input_rejects_out_of_range_values(tmp_path):
    from reefanalysis.dashboard import parse_indicators

    f = tmp_path / "invalid.json"
    f.write_text('{"lcc_percent": 101}')
    with pytest.raises(ValueError, match="lcc_percent"):
        parse_indicators(f)


def test_dashboard_cli_accepts_indicators_without_pipeline_results(tmp_path):
    f = tmp_path / "indicators.json"
    f.write_text('{"lcc_percent": 20, "ac_percent": 10}')
    out = tmp_path / "dashboard.html"
    assert main(["dashboard", "--indicators", str(f), "--out", str(out)]) == 0
    page = out.read_text()
    assert "20.000%" in page and "10.000%" in page
