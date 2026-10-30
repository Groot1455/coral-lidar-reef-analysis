"""Build a self-contained HTML reef assessment dashboard from pipeline outputs.

The page combines LiDAR-derived structure metrics with explicitly supplied
benthic/health outputs. It never infers biological cover or invents a Chi Index.
"""
from __future__ import annotations

import base64
import html
import json
import math
import re
from pathlib import Path
from typing import Any

CSS = """
:root{color-scheme:light dark;--bg:#f6f8f9;--card:#fff;--ink:#14232b;--mute:#5d707a;--line:#dfe6ea;--accent:#0b7f8c;--warn:#8a5100;--warnbg:#fff4e0;--poor:#c0392b;--fair:#e08e0b;--good:#3a9d5d;--excellent:#1f6fb2;--other:#7f8c8d}
@media (prefers-color-scheme:dark){:root{--bg:#0e1a20;--card:#15262e;--ink:#e6eef1;--mute:#93a8b2;--line:#264049;--accent:#4fc3d0;--warn:#f0b35a;--warnbg:#3a2c12;--poor:#ef6a5b;--fair:#f2b04a;--good:#5cc884;--excellent:#5ea8ec;--other:#9aa7a8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:26px 18px 52px}h1{font-size:1.8rem;line-height:1.2;margin:0 0 6px}h2{font-size:1.15rem;margin:30px 0 10px}
.sub{color:var(--mute);margin:0 0 18px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 16px;min-width:0}.k{color:var(--mute);font-size:.76rem;text-transform:uppercase;letter-spacing:.05em}.v{font-size:1.55rem;font-weight:700;color:var(--accent);overflow-wrap:anywhere}.detail{color:var(--mute);font-size:.82rem;margin-top:4px}
.note{background:var(--warnbg);color:var(--warn);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:14px 0}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line)}th{color:var(--mute);font-weight:600;font-size:.85rem}td.n{text-align:right;font-variant-numeric:tabular-nums}.scroll{overflow-x:auto}
.stack{display:flex;height:34px;border-radius:8px;overflow:hidden;border:1px solid var(--line);background:var(--line)}.hrow{display:grid;grid-template-columns:100px 1fr 76px;gap:10px;align-items:center;margin:9px 0}.track{background:var(--line);border-radius:6px;height:15px;overflow:hidden}.fill{height:100%}.pct{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
img{width:100%;height:auto;border-radius:10px;border:1px solid var(--line);background:#fff}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}footer{color:var(--mute);font-size:.8rem;margin-top:34px}
"""

LABELS = {
    "rugosity_global": ("Global rugosity (surface / planar area)", "{:.3f}"),
    "slope_mean_deg": ("Mean slope (degrees)", "{:.2f}"),
    "slope_std_deg": ("Slope standard deviation (degrees)", "{:.2f}"),
    "curvature_std": ("Curvature standard deviation (1/m)", "{:.3f}"),
    "tri_mean_m": ("Mean terrain ruggedness (m)", "{:.4f}"),
    "vrm_mean": ("Mean vector ruggedness measure", "{:.4f}"),
    "fractal_dimension": ("Fractal dimension", "{:.3f}"),
    "elevation_std_m": ("Elevation standard deviation (m)", "{:.3f}"),
}
HEALTH_ORDER = ["poor", "fair", "good", "excellent"]


def _card(k: str, v: str, detail: str | None = None) -> str:
    more = f'<div class="detail">{html.escape(detail)}</div>' if detail else ""
    return (f'<div class="card"><div class="k">{html.escape(k)}</div>'
            f'<div class="v">{html.escape(v)}</div>{more}</div>')


def _table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(
            f'<td class="{"n" if i else ""}">{html.escape(str(c))}</td>'
            for i, c in enumerate(r)
        ) + "</tr>"
        for r in rows
    )
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _finite_number(value: Any, field: str, low: float, high: float) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a number, not a boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric or null") from exc
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError(f"{field} must be between {low:g} and {high:g}")
    return number


def parse_indicators(source: str | Path) -> dict[str, Any]:
    """Read optional external LCC/AC percentages and an externally calculated CHI.

    JSON keys: site_name, survey_date, source, notes, lcc_percent, ac_percent,
    chi_score. CHI is an external value on the 0..1 scale and is never recomputed.
    """
    path = Path(source)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid indicator JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("Indicator JSON must contain one object")
    return {
        "site_name": str(raw.get("site_name") or "").strip(),
        "survey_date": str(raw.get("survey_date") or "").strip(),
        "source": str(raw.get("source") or "").strip(),
        "notes": str(raw.get("notes") or "").strip(),
        "lcc_percent": _finite_number(raw.get("lcc_percent"), "lcc_percent", 0, 100),
        "ac_percent": _finite_number(raw.get("ac_percent"), "ac_percent", 0, 100),
        "chi_score": _finite_number(raw.get("chi_score"), "chi_score", 0, 1),
    }


def parse_health(source: str | Path) -> dict[str, float]:
    """Read class percentages from `Poor: 86.24%` lines or a JSON object."""
    text = Path(source).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = None
    if isinstance(raw, dict):
        found = {
            str(k): _finite_number(v, str(k), 0, 100)
            for k, v in raw.items()
        }
    else:
        found = {}
        for name, val in re.findall(
            r"^\s*([A-Za-z][\w \-]*?)\s*[:=]\s*(-?\d+(?:\.\d+)?)\s*%?\s*$",
            text, flags=re.M,
        ):
            found[name.strip()] = _finite_number(val, name.strip(), 0, 100)  # type: ignore[assignment]
    if not found:
        raise ValueError(f"No 'Class: value%' lines found in {source}")
    rank = {n: i for i, n in enumerate(HEALTH_ORDER)}
    return dict(sorted(found.items(), key=lambda kv: (rank.get(kv[0].lower(), 99), kv[0])))  # type: ignore[arg-type]


def _health_section(health: dict[str, float]) -> str:
    def col(name: str) -> str:
        return f"var(--{name.lower()})" if name.lower() in HEALTH_ORDER else "var(--other)"

    total = sum(health.values())
    top = max(health, key=health.get)
    stack = "".join(
        f'<div title="{html.escape(n)} {v:.2f}%" style="width:{v:.4f}%;background:{col(n)}"></div>'
        for n, v in health.items() if v > 0
    )
    rows = "".join(
        f'<div class="hrow"><div><span class="sw" style="background:{col(n)}"></span>{html.escape(n)}</div>'
        f'<div class="track"><div class="fill" style="width:{v:.2f}%;background:{col(n)}"></div></div>'
        f'<div class="pct">{v:.2f}%</div></div>'
        for n, v in health.items()
    )
    warn = (f'<div class="note">Health-class percentages sum to {total:.2f}%, not 100%. '
            "Check the supplied input.</div>") if abs(total - 100) > 0.5 else ""
    return (
        "<h2>Health-class distribution</h2>"
        f'<div class="grid">{"".join(_card(n, f"{v:.2f}%") for n, v in health.items())}</div>'
        f'<p class="sub" style="margin-top:14px">Largest share: <b>{html.escape(top)}</b> ({health[top]:.2f}%)</p>'
        f'<div class="stack" role="img" aria-label="Stacked share of each health class">{stack}</div>'
        f'<div style="margin-top:14px">{rows}</div>{warn}'
        '<p class="detail">Class percentages are displayed as supplied; this dashboard does not recalculate the classification.</p>'
    )


def _number_text(value: Any, suffix: str = "") -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not available"
    return f"{number:.3f}{suffix}" if math.isfinite(number) else "Not available"


def _indicator_section(metrics: dict[str, Any] | None, indicators: dict[str, Any] | None) -> str:
    reef = (metrics or {}).get("reef_structure") or {}
    chi = (metrics or {}).get("chi_index") or {}
    ext = indicators or {}

    sc = reef.get("SC_mean_m")
    vr = reef.get("VR_mean_m")
    lcc = ext.get("lcc_percent")
    ac = ext.get("ac_percent")
    external_chi = ext.get("chi_score")

    cards = [
        _card("SC · local elevation SD", _number_text(sc, " m"), "Mean moving-window standard deviation" if sc is not None else "Run pipeline to calculate"),
        _card("VR · local elevation range", _number_text(vr, " m"), "Mean moving-window max − min" if vr is not None else "Run pipeline to calculate"),
        _card("LCC · live coral cover", _number_text(lcc, "%"), "Externally supplied benthic classification" if lcc is not None else "Awaiting benthic classification"),
        _card("AC · algal cover", _number_text(ac, "%"), "Externally supplied benthic classification" if ac is not None else "Awaiting benthic classification"),
    ]
    if external_chi is not None:
        cards.append(_card("CHI · external score", f"{external_chi:.3f} / 1.000", "Supplied by external script; not recomputed here"))
    elif chi.get("status") == "ok":
        val = chi.get("chi_mean", chi.get("chi_score", chi.get("mean")))
        cards.append(_card("CHI · pipeline score", _number_text(val), "Calculated by the configured Chi Index implementation"))
    else:
        cards.append(_card("CHI · Chi Index", "Not implemented", "Requires the verified base-paper definition"))

    notes = []
    if ext.get("site_name"):
        notes.append(f"Site: {html.escape(ext['site_name'])}")
    if ext.get("survey_date"):
        notes.append(f"Survey date: {html.escape(ext['survey_date'])}")
    if ext.get("source"):
        notes.append(f"Indicator source: {html.escape(ext['source'])}")
    meta = f'<p class="sub">{" · ".join(notes)}</p>' if notes else ""
    extra_note = (
        '<div class="note">SC and VR describe reef surface structure, not coral species or live cover. '
        'LCC and AC require a benthic classification input; LiDAR elevation alone does not identify live coral or algae. '
        "The Chi Index remains disabled until its equation is verified against the project's base paper.</div>"
    )
    if ext.get("notes"):
        extra_note += f'<p class="detail">Notes: {html.escape(ext["notes"])}</p>'
    return f"<h2>Core reef indicators</h2>{meta}<div class='grid'>{''.join(cards)}</div>{extra_note}"


def build_dashboard(
    results_dir: str | Path | None,
    out_file: str | Path,
    health: dict[str, float] | None = None,
    indicators: dict[str, Any] | None = None,
) -> Path:
    """Build the combined dashboard from pipeline outputs and optional external inputs."""
    out_file = Path(out_file)
    results_dir = Path(results_dir) if results_dir else None
    mfile = results_dir / "metrics.json" if results_dir else None
    m = json.loads(mfile.read_text(encoding="utf-8")) if mfile and mfile.exists() else None
    if m is None and not health and not indicators:
        raise FileNotFoundError("Nothing to show: no metrics.json, health classes, or indicators supplied")

    title = "Coral reef assessment dashboard"
    parts = [f"<h1>{title}</h1>", '<p class="sub">LiDAR-derived reef structure with separately supplied biological indicators.</p>']
    parts.append(_indicator_section(m, indicators))

    if health:
        parts.append(_health_section(health))

    if m:
        cx = m.get("complexity") or {}
        rs = m.get("reef_structure") or {}
        cd, ob = m.get("change_detection"), m.get("obia")
        kpis = [
            _card("Global rugosity", _number_text(cx.get("rugosity_global"))),
            _card("Fractal dimension", _number_text(cx.get("fractal_dimension"))),
            _card("Mean slope", _number_text(cx.get("slope_mean_deg"), "°")),
            _card("DEM grid", f"{m.get('dem_shape', ['?', '?'])[1]}×{m.get('dem_shape', ['?', '?'])[0]}",
                  f"Cell size: {m.get('dem_resolution_m', 'n/a')} m"),
        ]
        if cd:
            kpis.append(_card("Net volume change", _number_text(cd.get("net_volume_m3"), " m³")))
        parts.append(f'<h2>LiDAR survey summary</h2><p class="sub">Input: {html.escape(str(m.get("input", "unknown")))} · {int(m.get("n_points_used", 0)):,} points used</p>')
        parts.append(f'<div class="grid">{"".join(kpis)}</div>')

        png = results_dir / "overview.png" if results_dir else None
        if png and png.exists():
            b64 = base64.b64encode(png.read_bytes()).decode("ascii")
            parts.append(f'<h2>Spatial metric maps</h2><img alt="Maps of DEM, terrain features, structural complexity, vertical relief and classifications" src="data:image/png;base64,{b64}">')

        if cx:
            parts.append("<h2>Additional structural metrics</h2>" + _table(
                ["Metric", "Value"],
                [[LABELS[k][0], LABELS[k][1].format(v)] for k, v in cx.items() if k in LABELS and isinstance(v, (int, float))],
            ))
        if rs:
            structure_rows = [
                ["Structural complexity (local elevation SD)", f"{rs.get('SC_mean_m', float('nan')):.4f} m", f"{rs.get('SC_p95_m', float('nan')):.4f} m"],
                ["Vertical relief (local max − min)", f"{rs.get('VR_mean_m', float('nan')):.4f} m", f"{rs.get('VR_p95_m', float('nan')):.4f} m"],
            ]
            parts.append("<h2>SC and VR summary</h2>" + _table(["Metric", "Mean", "95th percentile"], structure_rows))
        if ob:
            parts.append(f"<h2>OBIA classes ({ob['n_objects']} objects)</h2>" + _table(
                ["Class", "Heuristic name", "Area (m²)", "% area"],
                [[str(c["class"]), c["heuristic_name"], f"{c['area_m2']:.1f}", f"{c['pct_area']:.1f}"] for c in ob["classes"]],
            ))
            parts.append('<p class="detail">OBIA class names are heuristic (ranked by rugosity), not field-validated.</p>')
        if cd:
            parts.append("<h2>Depth change detection</h2>" + _table(
                ["Quantity", "Value"], [[k, f"{v:.3f}"] for k, v in cd.items()],
            ))

    parts.append("<footer>Generated by reefanalysis. SC and VR are morphology metrics; ecological condition requires independent biological observations and field validation.</footer>")
    doc = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{title}</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>"
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(doc, encoding="utf-8")
    return out_file
