#!/usr/bin/env python3
"""Ringside — coverage report generator (stdlib only, cross-platform).

Reads a Ringside *scenario JSON* (schema documented in
skills/test-architect/references/requirements-first-scenarios.md #8) and renders:

  * ringside-report.html  — a self-contained, theme-aware page a person with zero
                            Jira context can read: a headline verdict, summary
                            tiles, coverage-by-requirement (with THIN / UNCOVERED
                            flags), the full traceable scenario list, and the gaps
                            & recorded assumptions.
  * ringside-matrix.csv    — the requirement -> scenario -> coverage matrix,
                            re-importable into Jira / a spreadsheet.

Security posture: every piece of ticket-sourced text is treated as UNTRUSTED and
HTML-escaped before it reaches the report; the report is fully static (no
JavaScript at all), so a malicious ticket title can never execute in a viewer's
browser. The CSV neutralizes formula-injection. The generator reads only the
scenario JSON — it never touches secrets.

Usage:
    python ringside_report.py <scenarios.json> [--out <dir>]
"""
import csv
import html
import io
import json
import os
import sys

# Console encoding: the report carries emoji/box glyphs and the CLI prints an
# em-dash; force UTF-8 so a Windows console (cp1252) never mangles or chokes on
# output — mirrors the reconfigure the other Ringmaster hooks use.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Enum vocabularies — kept in lock-step with the scenario-JSON schema (reference #8).
VALID_PRIORITIES = ("P1", "P2", "P3")
VALID_SOURCES = ("jira", "user", "ringside")
VALID_CATEGORIES = (
    "happy", "boundary", "failure", "state",
    "concurrency", "security", "a11y", "perf",
)
# Ringside is satisfied with a requirement only when it is exercised on BOTH a
# happy path AND a failure path — failure paths are where real incidents hide, so
# a failure gap is a red flag even when boundaries are covered. Boundary coverage
# is tracked and shown, but its absence alone is advisory, not a THIN trigger.
_CORE_COVERAGE = ("happy", "failure")

CSV_HEADER = (
    "requirement_id", "requirement_text", "scenario_id", "given", "when", "then",
    "test_type", "priority", "source", "category", "edge_case",
    "assumption_based", "coverage_flag",
)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate(data):
    """Return a list of human-readable errors; an empty list means valid."""
    errors = []
    if not isinstance(data, dict):
        return ["scenario data must be a JSON object"]

    requirements = data.get("requirements")
    scenarios = data.get("scenarios")
    if not isinstance(requirements, list):
        errors.append("requirements must be a list")
        requirements = []
    if not isinstance(scenarios, list):
        errors.append("scenarios must be a list")
        scenarios = []

    req_ids = set()
    for i, r in enumerate(requirements):
        where = "requirements[%d]" % i
        if not isinstance(r, dict):
            errors.append("%s must be an object" % where)
            continue
        rid = r.get("id")
        if not rid:
            errors.append("%s.id is required" % where)
        elif not isinstance(rid, str):
            errors.append("%s.id must be a string" % where)
        elif rid in req_ids:
            errors.append("%s.id '%s' is duplicated" % (where, rid))
        else:
            req_ids.add(rid)
        if not (isinstance(r.get("text"), str) and r.get("text").strip()):
            errors.append("%s.text is required" % where)

    seen = set()
    for i, s in enumerate(scenarios):
        where = "scenarios[%d]" % i
        if not isinstance(s, dict):
            errors.append("%s must be an object" % where)
            continue
        sid = s.get("id")
        if not sid:
            errors.append("%s.id is required" % where)
        elif not isinstance(sid, str):
            errors.append("%s.id must be a string" % where)
        elif sid in seen:
            errors.append("%s.id '%s' is duplicated" % (where, sid))
        else:
            seen.add(sid)
        rid = s.get("requirementId")
        if not rid:
            errors.append("%s.requirementId is required" % where)
        elif not isinstance(rid, str):
            errors.append("%s.requirementId must be a string" % where)
        elif rid not in req_ids:
            errors.append("%s.requirementId '%s' references unknown requirement"
                          % (where, rid))
        for field in ("given", "when", "then"):
            if not (isinstance(s.get(field), str) and s.get(field).strip()):
                errors.append("%s.%s is required" % (where, field))
        if not (isinstance(s.get("testType"), str) and s.get("testType").strip()):
            errors.append("%s.testType is required" % where)
        if s.get("priority") not in VALID_PRIORITIES:
            errors.append("%s.priority must be one of %s" % (where, list(VALID_PRIORITIES)))
        if s.get("source") not in VALID_SOURCES:
            errors.append("%s.source must be one of %s" % (where, list(VALID_SOURCES)))
        if s.get("category") not in VALID_CATEGORIES:
            errors.append("%s.category must be one of %s" % (where, list(VALID_CATEGORIES)))

    # Optional sections: reject shapes that would later crash the renderer.
    meta = data.get("meta")
    if meta is not None and not isinstance(meta, dict):
        errors.append("meta must be an object")
    for key in ("gaps", "assumptions"):
        val = data.get(key)
        if val is None:
            continue
        if not isinstance(val, list):
            errors.append("%s must be a list" % key)
            continue
        for j, item in enumerate(val):
            if not isinstance(item, dict):
                errors.append("%s[%d] must be an object" % (key, j))
    return errors


# --------------------------------------------------------------------------- #
# Coverage analysis
# --------------------------------------------------------------------------- #
def coverage_by_requirement(data):
    """Map each requirement id -> coverage facts, in requirement order.

    thin      = has scenarios but is missing a core dimension — a happy path
                and/or a failure path (`missing` names which). A failure-path gap
                is a Ringside red flag even when boundaries are covered, because
                failure paths are where real incidents hide.
    uncovered = no scenarios at all.
    """
    requirements = data.get("requirements") or []
    scenarios = data.get("scenarios") or []
    by_req = {}
    for r in requirements:
        if isinstance(r, dict) and r.get("id"):
            by_req[r["id"]] = []
    for s in scenarios:
        if isinstance(s, dict) and s.get("requirementId") in by_req:
            by_req[s["requirementId"]].append(s)

    result = {}
    for rid, scns in by_req.items():
        by_cat = {}
        for s in scns:
            cat = s.get("category", "?")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        total = len(scns)
        # Which core dimensions are absent (stable order for the report).
        missing = [dim for dim in _CORE_COVERAGE if not by_cat.get(dim)]
        result[rid] = {
            "total": total,
            "byCategory": by_cat,
            "scenarioIds": [s.get("id") for s in scns],
            "hasHappy": bool(by_cat.get("happy")),
            "hasBoundary": bool(by_cat.get("boundary")),
            "hasFailure": bool(by_cat.get("failure")),
            "missing": missing,
            "thin": total > 0 and bool(missing),
            "uncovered": total == 0,
        }
    return result


def _flag(cov_row):
    if cov_row["uncovered"]:
        return "UNCOVERED"
    if cov_row["thin"]:
        return "THIN"
    return "OK"


# --------------------------------------------------------------------------- #
# Rendering — HTML
# --------------------------------------------------------------------------- #
def _esc(value):
    """HTML-escape any (untrusted) value, including quotes."""
    return html.escape("" if value is None else str(value), quote=True)


# Design tokens: a "front-row / spotlight" identity. Warm violet-biased neutrals
# with a single plum accent, kept clear of the semantic ok/thin/bad trio. Both
# themes are defined at the token level; components never reach past a token.
_STYLE = """
*{box-sizing:border-box}
:root{color-scheme:light;
--bg:#f7f5fb;--surface:#ffffff;--card:#f3f0f9;--line:#e6e0f0;
--fg:#1a1523;--muted:#6b6480;--accent:#6d28d9;--accent-weak:#efe9fb;
--ok:#15803d;--thin:#a35a00;--bad:#c0243a;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
--bg:#131019;--surface:#1a1523;--card:#20192c;--line:#2f2740;
--fg:#ece7f4;--muted:#9c93ac;--accent:#b39df7;--accent-weak:#241c33;
--ok:#4ac06a;--thin:#e0a53a;--bad:#f2687f;}}
:root[data-theme="dark"]{color-scheme:dark;
--bg:#131019;--surface:#1a1523;--card:#20192c;--line:#2f2740;
--fg:#ece7f4;--muted:#9c93ac;--accent:#b39df7;--accent-weak:#241c33;
--ok:#4ac06a;--thin:#e0a53a;--bad:#f2687f;}
:root[data-theme="light"]{color-scheme:light;
--bg:#f7f5fb;--surface:#ffffff;--card:#f3f0f9;--line:#e6e0f0;
--fg:#1a1523;--muted:#6b6480;--accent:#6d28d9;--accent-weak:#efe9fb;
--ok:#15803d;--thin:#a35a00;--bad:#c0243a;}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.wrap{max-width:960px;margin:0 auto;padding:40px 22px 72px}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
font-size:.92em}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;
color:var(--muted);margin:0 0 12px}
.masthead{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:28px}
.brand{display:inline-flex;align-items:center;gap:8px;font-weight:800;font-size:15px;letter-spacing:-.01em}
.brand .ring{color:var(--accent);font-size:13px}
.masthead h1{font-size:31px;line-height:1.08;letter-spacing:-.022em;margin:14px 0 10px;
text-wrap:balance;font-weight:800}
.masthead .meta{color:var(--muted);font-size:13px;margin:0}
.masthead .meta b{color:var(--fg);font-weight:600}
.verdict{margin-top:18px;padding:13px 16px;border-radius:11px;font-weight:600;font-size:14px;
border:1px solid var(--line);background:var(--card);display:flex;gap:10px;align-items:baseline}
.verdict::before{content:"Verdict";font-size:10px;font-weight:800;letter-spacing:.12em;
text-transform:uppercase;color:var(--muted);flex:none}
.verdict.bad{border-color:var(--bad);color:var(--bad);background:transparent}
.verdict.thin{border-color:var(--thin);color:var(--thin);background:transparent}
.verdict.ok{border-color:var(--ok);color:var(--ok);background:transparent}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(116px,1fr));gap:10px;margin:0 0 36px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .n{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em;line-height:1}
.kpi .l{color:var(--muted);font-size:11.5px;margin-top:5px;letter-spacing:.02em}
.kpi.warn .n{color:var(--thin)} .kpi.crit .n{color:var(--bad)}
section{margin:0 0 34px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:10px 13px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
font-weight:700;white-space:nowrap;background:var(--card)}
tbody tr:last-child td{border-bottom:none}
.pri{font-variant-numeric:tabular-nums;font-weight:700}
.badge{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;
font-size:11px;font-weight:700;border:1px solid currentColor;white-space:nowrap;letter-spacing:.02em}
.badge::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
.s-ok{color:var(--ok)} .s-thin{color:var(--thin)} .s-bad{color:var(--bad)}
.src{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:10.5px;
text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.edge{color:var(--bad);font-weight:800}
.card{border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:0 0 14px;background:var(--surface)}
.card>header{display:flex;align-items:center;justify-content:space-between;gap:12px;
padding:13px 16px;background:var(--card);border-bottom:1px solid var(--line)}
.card .rid{font-weight:700}
.card .rtext{color:var(--muted);font-weight:400;font-size:13px}
.card .scroll{border:none;border-radius:0}
.card .empty{padding:15px 16px;color:var(--bad);font-size:13px}
.gwt b{color:var(--accent);font-weight:700;font-size:10px;letter-spacing:.05em;
text-transform:uppercase;margin:0 3px 0 0}
.tag{display:inline-block;background:var(--accent-weak);color:var(--accent);border-radius:6px;
padding:1px 7px;font-size:10.5px;font-weight:700;letter-spacing:.02em;text-transform:uppercase}
ul{margin:8px 0 0;padding-left:20px} li{margin:4px 0}
li .mono{color:var(--accent);font-weight:600}
footer{color:var(--muted);font-size:12px;margin-top:46px;border-top:1px solid var(--line);
padding-top:18px;line-height:1.7}
footer b{color:var(--fg)}
*:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""

_STATUS_CLASS = {"OK": "s-ok", "THIN": "s-thin", "UNCOVERED": "s-bad"}


def _kpi(n, label, cls=""):
    return ('<div class="kpi %s"><div class="n">%s</div><div class="l">%s</div></div>'
            % (cls, _esc(n), _esc(label)))


def render_html(data):
    """Return the full self-contained HTML report as a string."""
    # Defensive reads: even if validate() is bypassed, a malformed element must
    # never crash the renderer — filter to the well-formed shapes.
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    requirements = [r for r in (data.get("requirements") or []) if isinstance(r, dict)]
    scenarios = [s for s in (data.get("scenarios") or []) if isinstance(s, dict)]
    gaps = [g for g in (data.get("gaps") or []) if isinstance(g, dict)]
    assumptions = [a for a in (data.get("assumptions") or []) if isinstance(a, dict)]
    cov = coverage_by_requirement(data)
    req_text = {r.get("id"): r.get("text", "") for r in requirements if isinstance(r, dict)}

    n_edge = sum(1 for s in scenarios if s.get("edgeCase"))
    n_thin = sum(1 for c in cov.values() if c["thin"])
    n_unc = sum(1 for c in cov.values() if c["uncovered"])

    # Ringside's headline verdict — never satisfied until the edges are covered.
    if n_unc:
        vclass = "bad"
        vtext = ("%d requirement%s left UNCOVERED — Ringside will not sign off on this."
                 % (n_unc, "s" if n_unc != 1 else ""))
    elif n_thin:
        vclass = "thin"
        vtext = ("%d requirement%s not exercised on both a happy and a failure path "
                 "— the edges where incidents hide are exposed."
                 % (n_thin, "s" if n_thin != 1 else ""))
    elif requirements:
        vclass = "ok"
        vtext = ("Every requirement carries boundary and failure coverage. "
                 "Ringside is, grudgingly, satisfied.")
    else:
        vclass = "thin"
        vtext = "No requirements read from the source of truth yet."

    p = []
    p.append("<!doctype html>")
    p.append('<html lang="en"><head><meta charset="utf-8">')
    p.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    p.append("<title>Ringside coverage — %s</title>" % _esc(meta.get("project", "")))
    p.append("<style>%s</style></head><body>" % _STYLE)
    p.append('<div class="wrap">')

    # Masthead
    p.append('<header class="masthead">')
    p.append('<div class="brand"><span class="ring">&#9673;</span> Ringside</div>')
    p.append('<p class="eyebrow" style="margin:14px 0 0">'
             "Test Architect &middot; requirements-first coverage</p>")
    p.append("<h1>Coverage report &mdash; %s</h1>" % _esc(meta.get("project", "—")))
    srcs_list = meta.get("sources") if isinstance(meta.get("sources"), (list, tuple)) else []
    bits = ["source of truth <b>%s</b>" % _esc(meta.get("tracker", "—"))]
    srcs = " &middot; ".join(_esc(s) for s in srcs_list)
    if srcs:
        bits.append(srcs)
    bits.append("generated %s" % _esc(meta.get("generatedAt", "—")))
    p.append('<p class="meta">%s</p>' % "  &middot;  ".join(bits))
    p.append('<div class="verdict %s">%s</div>' % (vclass, _esc(vtext)))
    p.append("</header>")

    # KPI tiles — summary before detail
    p.append('<section class="kpis">')
    p.append(_kpi(len(requirements), "requirements"))
    p.append(_kpi(len(scenarios), "scenarios"))
    p.append(_kpi(n_edge, "edge cases"))
    p.append(_kpi(n_thin, "thin", "warn" if n_thin else ""))
    p.append(_kpi(n_unc, "uncovered", "crit" if n_unc else ""))
    p.append(_kpi(len(assumptions), "assumptions"))
    p.append("</section>")

    # Coverage by requirement
    p.append("<section>")
    p.append('<p class="eyebrow">Coverage by requirement</p>')
    p.append('<div class="scroll"><table><thead><tr>'
             "<th>Requirement</th><th>Description</th><th>Scenarios</th>"
             "<th>Categories</th><th>Status</th></tr></thead><tbody>")
    for rid, c in cov.items():
        flag = _flag(c)
        cats = ", ".join("%s&middot;%d" % (_esc(k), v)
                         for k, v in c["byCategory"].items()) or "—"
        status = '<span class="badge %s">%s</span>' % (_STATUS_CLASS[flag], flag)
        if flag == "THIN" and c.get("missing"):
            status += (' <span class="src">needs %s</span>'
                       % _esc(", ".join(c["missing"])))
        p.append('<tr><td class="mono">%s</td><td>%s</td>'
                 '<td class="pri">%d</td><td>%s</td>'
                 '<td>%s</td></tr>'
                 % (_esc(rid), _esc(req_text.get(rid, "")), c["total"], cats, status))
    p.append("</tbody></table></div></section>")

    # Scenarios grouped by requirement (cards)
    p.append("<section>")
    p.append('<p class="eyebrow">Scenarios &middot; traceable to requirements</p>')
    for rid, c in cov.items():
        flag = _flag(c)
        p.append('<div class="card"><header>'
                 '<span><span class="rid mono">%s</span> <span class="rtext">%s</span></span>'
                 '<span class="badge %s">%s</span></header>'
                 % (_esc(rid), _esc(req_text.get(rid, "")), _STATUS_CLASS[flag], flag))
        rows = [s for s in scenarios if s.get("requirementId") == rid]
        if not rows:
            p.append('<div class="empty">No scenarios yet — this requirement is '
                     "UNCOVERED.</div></div>")
            continue
        p.append('<div class="scroll"><table><thead><tr>'
                 "<th>ID</th><th>Given / When / Then</th><th>Type</th><th>Pri</th>"
                 "<th>Source</th><th>Edge</th><th>Category</th></tr></thead><tbody>")
        for s in rows:
            gwt = ('<span class="gwt"><b>Given</b>%s <b>When</b>%s <b>Then</b>%s</span>'
                   % (_esc(s.get("given")), _esc(s.get("when")), _esc(s.get("then"))))
            if s.get("assumptionBased"):
                gwt += ' <span class="tag">assumption</span>'
            p.append('<tr><td class="mono">%s</td><td>%s</td><td>%s</td>'
                     '<td class="pri">%s</td><td class="src">%s</td>'
                     '<td>%s</td><td>%s</td></tr>'
                     % (_esc(s.get("id")), gwt, _esc(s.get("testType")),
                        _esc(s.get("priority")), _esc(s.get("source")),
                        '<span class="edge">&#10004;</span>' if s.get("edgeCase") else "",
                        _esc(s.get("category"))))
        p.append("</tbody></table></div></div>")
    p.append("</section>")

    # Gaps & recorded assumptions
    if gaps or assumptions:
        p.append("<section>")
        p.append('<p class="eyebrow">Gaps &amp; recorded assumptions</p>')
        if gaps:
            p.append('<p class="meta"><b>Gaps raised with the author</b></p><ul>')
            for g in gaps:
                p.append('<li><span class="mono">%s</span> %s — <i>%s</i> (%s)</li>'
                         % (_esc(g.get("id")), _esc(g.get("gap")),
                            _esc(g.get("whyItMatters")), _esc(g.get("status"))))
            p.append("</ul>")
        if assumptions:
            p.append('<p class="meta" style="margin-top:14px"><b>Assumptions carried into '
                     "scenarios — a guess until confirmed</b></p><ul>")
            for a in assumptions:
                p.append('<li><span class="mono">%s</span> %s — <i>%s</i></li>'
                         % (_esc(a.get("id")), _esc(a.get("text")), _esc(a.get("reason"))))
            p.append("</ul>")
        p.append("</section>")

    p.append('<footer>Generated by <b>Ringside</b> — the Test Architect in requirements-first '
             "mode. Every scenario traces to a requirement in the source of truth. Nothing here "
             "trusts the code the developers wrote — it is what the ticket says must be true.</footer>")
    p.append("</div></body></html>")
    return "\n".join(p)


# --------------------------------------------------------------------------- #
# Rendering — CSV
# --------------------------------------------------------------------------- #
def _csv_safe(value):
    """Neutralize CSV formula injection: ticket text is untrusted, and a cell
    beginning with = + - @ (or a leading tab/CR) can execute as a formula when
    the matrix is opened in Excel/Sheets. Prefix such a cell with a quote so it
    is treated as literal text."""
    s = "" if value is None else str(value)
    if s and s[0] in "=+-@\t\r\n":
        return "'" + s
    return s


def render_csv(data):
    """Return the requirement -> scenario -> coverage matrix as CSV text."""
    requirements = data.get("requirements") or []
    scenarios = [s for s in (data.get("scenarios") or []) if isinstance(s, dict)]
    cov = coverage_by_requirement(data)
    req_text = {r.get("id"): r.get("text", "") for r in requirements if isinstance(r, dict)}

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)

    def emit(row):
        writer.writerow([_csv_safe(c) for c in row])

    for rid in cov:
        flag = _flag(cov[rid])
        rows = [s for s in scenarios if s.get("requirementId") == rid]
        if not rows:
            emit([rid, req_text.get(rid, ""), "", "", "", "",
                  "", "", "", "", "", "", flag])
            continue
        for s in rows:
            emit([
                rid, req_text.get(rid, ""), s.get("id", ""),
                s.get("given", ""), s.get("when", ""), s.get("then", ""),
                s.get("testType", ""), s.get("priority", ""), s.get("source", ""),
                s.get("category", ""),
                "yes" if s.get("edgeCase") else "no",
                "yes" if s.get("assumptionBased") else "no",
                flag,
            ])
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Write + CLI
# --------------------------------------------------------------------------- #
def write_report(data, out_dir):
    """Write both report files into out_dir; return (html_path, csv_path)."""
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "ringside-report.html")
    csv_path = os.path.join(out_dir, "ringside-matrix.csv")
    with open(html_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(render_html(data))
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(render_csv(data))
    return html_path, csv_path


def main(argv):
    """CLI: ringside_report.py <scenarios.json> [--out <dir>]. Returns an exit code."""
    path = None
    out_dir = "."
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--out":
            i += 1
            if i >= len(argv):
                print("error: --out needs a directory", file=sys.stderr)
                return 2
            out_dir = argv[i]
        elif arg in ("-h", "--help"):
            print(main.__doc__)
            return 0
        elif not arg.startswith("--"):
            path = arg
        i += 1

    if not path:
        print("usage: ringside_report.py <scenarios.json> [--out <dir>]", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError) as exc:
        # RecursionError: a deeply-nested hostile JSON. ValueError covers JSON
        # decode + decode errors. Fail gracefully, never with a raw traceback.
        print("error: could not read scenario JSON: %s" % exc, file=sys.stderr)
        return 2

    errs = validate(data)
    if errs:
        print("Ringside: %d problem(s) in the scenario JSON — fix these first:" % len(errs),
              file=sys.stderr)
        for e in errs:
            print("  - %s" % e, file=sys.stderr)
        return 1

    try:
        html_path, csv_path = write_report(data, out_dir)
    except Exception as exc:  # defense in depth — a validated doc should never reach here
        print("error: failed to render report: %s" % exc, file=sys.stderr)
        return 2
    print("Ringside report written:")
    print("  HTML: %s" % html_path)
    print("  CSV:  %s" % csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
