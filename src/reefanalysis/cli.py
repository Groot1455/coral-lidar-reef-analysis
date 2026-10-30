"""Command line interface."""
from __future__ import annotations

import argparse
import json
import logging

from .config import Config


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="reefanalysis", description="Coral reef structure analysis from LiDAR data")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run the full pipeline")
    r.add_argument("--input", required=True, help="point cloud (csv/npy/las/laz)")
    r.add_argument("--compare", help="second survey for depth change detection")
    r.add_argument("--out", help="output directory (overrides REEF_OUTPUT_DIR)")

    d = sub.add_parser("dashboard", help="build a self-contained HTML dashboard from a results folder")
    d.add_argument("--results", default=None, help="folder with metrics.json (optional if --health or --indicators is given)")
    d.add_argument("--health", default=None, help="text/JSON file with health-class percentages")
    d.add_argument("--indicators", default=None, help="JSON file with optional LCC, AC and external CHI values")
    d.add_argument("--out", default=None, help="HTML file to write (default <results>/dashboard.html)")

    g = sub.add_parser("generate-sample", help="write synthetic sample surveys")
    g.add_argument("--out", default="data/sample")

    a = p.parse_args(argv)
    cfg = Config.from_env()
    logging.basicConfig(level=cfg.log_level, format="%(levelname)s %(name)s: %(message)s")

    if a.cmd == "generate-sample":
        from .sample_data import write_samples

        print("\n".join(write_samples(a.out)))
        return 0

    if a.cmd == "dashboard":
        from pathlib import Path

        from .dashboard import build_dashboard

        from .dashboard import parse_health, parse_indicators

        health = parse_health(a.health) if a.health else None
        indicators = parse_indicators(a.indicators) if a.indicators else None
        results = a.results or (None if health or indicators else cfg.output_dir)
        default_out = Path(results or ".") / "dashboard.html"
        print(build_dashboard(results, a.out or default_out, health, indicators))
        return 0

    from .pipeline import run

    if a.out:
        cfg.output_dir = a.out
    res = run(a.input, a.compare, cfg)
    print(json.dumps({k: res[k] for k in ("complexity", "reef_structure", "chi_index")}, indent=2))
    print(f"Full results: {cfg.output_dir}/metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
