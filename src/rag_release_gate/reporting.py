"""Self-contained HTML, JSON, Markdown and JUnit reports from one canonical result."""

import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from .io import write_jsonl


def number(value):
    return "N/A" if value is None else f"{value:.3f}"


def write_reports(output: Path, report: dict, traces: dict):
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )
    for stage, rows in traces.items():
        write_jsonl(output / f"{stage}.jsonl", rows.values())
    gate = report["gate"]
    status = "PASS" if gate["passed"] else "BLOCKED"
    lines = [
        f"# RAG Release Gate: {status}",
        "",
        f"Engine: `{report['engine']}` · Cases: {gate['case_count']} · Candidate: `{report['candidate_profile']}`",
        "",
        "| Metric | Baseline | Candidate | Delta | Paired cases | 95% cluster CI |",
        "|---|---:|---:|---:|---:|---|",
    ]
    rows = []
    for metric, values in gate["metrics"].items():
        interval = values["ci"]
        ci = f"[{number(interval['low'])}, {number(interval['high'])}]" if interval else "N/A"
        cells = [
            metric,
            number(values["baseline"]),
            number(values["candidate"]),
            number(values["delta"]),
            f"{values['n']}/{values['expected']}",
            ci,
        ]
        lines.append("| " + " | ".join(cells) + " |")
        rows.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells) + "</tr>")
    lines += [
        "",
        f"Candidate application p95 latency: {gate['p95_latency_ms']['candidate']:.2f} ms (judge time excluded).",
        "",
        "Builtin metrics are deterministic checks. RAGAS and DeepEval scores appear only when those engines run.",
        "",
    ]
    if gate["violations"]:
        lines += ["## Release violations", ""] + [f"- {v}" for v in gate["violations"]]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    suite = ET.Element(
        "testsuite", name="rag-release-gate", tests="1", failures=str(int(not gate["passed"]))
    )
    test = ET.SubElement(suite, "testcase", name="release-policy", classname="rag.release")
    if not gate["passed"]:
        ET.SubElement(test, "failure", message="RAG release blocked").text = "\n".join(
            gate["violations"]
        )
    ET.ElementTree(suite).write(output / "junit.xml", encoding="utf-8", xml_declaration=True)
    details = []
    for row in report["cases"]:
        case = row["case"]
        candidate = row["candidate"]
        failed = [
            s
            for s in candidate["scores"]
            if s["error"] or (s["applicable"] and s["value"] is not None and s["value"] < 1)
        ]
        score_rows = "".join(
            f"<tr><td>{html.escape(s['metric'])}</td><td>{number(s['value'])}</td><td>{html.escape(s['error'] or s['reason'])}</td></tr>"
            for s in candidate["scores"]
        )
        context_html = "".join(
            f"<details><summary>{html.escape(c['id'])}</summary><p>{html.escape(c['text'])}</p></details>"
            for c in candidate["trace"]["contexts"]
        )
        details.append(f"""<details class="case" data-category="{html.escape(case["category"], quote=True)}" data-imperfect="{str(bool(failed)).lower()}">
<summary><span class="tag">{html.escape(case["category"])}</span><b>{html.escape(case["id"])}</b> {html.escape(case["question"])}<span class="severity">{html.escape(case["severity"])}</span></summary>
<div class="answers"><div><h3>Baseline answer</h3><p>{html.escape(row["baseline"]["trace"]["answer"] or row["baseline"]["trace"]["error"] or "")}</p></div><div><h3>Candidate answer</h3><p>{html.escape(candidate["trace"]["answer"] or candidate["trace"]["error"] or "")}</p></div></div>
<p class="reference"><b>Reference:</b> {html.escape(case["reference"])}</p><div class="scroll"><table><thead><tr><th>Candidate metric</th><th>Score</th><th>Evidence / reason</th></tr></thead><tbody>{score_rows}</tbody></table></div>{context_html}</details>""")
    violations = "".join(f"<li>{html.escape(v)}</li>" for v in gate["violations"])
    categories = "".join(
        f"<option>{html.escape(c)}</option>"
        for c in sorted({r["case"]["category"] for r in report["cases"]})
    )
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RAG Release Gate · {status}</title><style>
:root{{font-family:Inter,system-ui,sans-serif;color:#21312e;background:#f3f6f3;font-size:15px}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1240px;margin:0 auto;padding:40px 28px}}header{{display:flex;justify-content:space-between;gap:20px;align-items:center;border-bottom:1px solid #cbd8d0;padding-bottom:28px}}.eyebrow{{text-transform:uppercase;letter-spacing:2px;font-size:11px;color:#477566;font-weight:800}}h1{{font-size:38px;letter-spacing:-1.5px;margin:9px 0}}h2{{font-size:22px;margin-top:36px}}h3{{font-size:12px;text-transform:uppercase;color:#547268}}.status{{padding:12px 22px;border-radius:8px;background:{"#d7eee1" if gate["passed"] else "#f8dcd6"};color:{"#176542" if gate["passed"] else "#8d2e1b"};font-weight:800;letter-spacing:1px}}.meta{{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}}.card{{background:white;border:1px solid #d9e2dc;border-radius:9px;padding:17px 22px;flex:1;min-width:160px}}.card b{{display:block;font-size:26px;margin-top:5px}}.muted{{color:#65766e;font-size:13px}}table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}th{{text-align:left;background:#e5ede7;font-size:11px;letter-spacing:.3px;text-transform:uppercase}}td,th{{padding:12px 14px;border-bottom:1px solid #e3e9e4;vertical-align:top}}td:first-child{{font-family:ui-monospace,monospace}}.scroll{{overflow-x:auto;border:1px solid #d9e2dc;border-radius:8px}}.note{{padding:15px 18px;border-left:3px solid #4b876c;background:#e5eee6;line-height:1.6;margin:20px 0}}.case{{background:#fff;border:1px solid #d9e2dc;border-radius:8px;padding:16px;margin:12px 0}}summary{{cursor:pointer;line-height:1.7}}.tag{{font-size:10px;background:#eaf0ea;padding:4px 7px;border-radius:4px;margin-right:9px}}.severity{{color:#90654b;font-size:11px;margin-left:9px}}.answers{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}p{{line-height:1.65;overflow-wrap:anywhere}}.reference{{color:#5b7065;border-top:1px solid #e5ebe6;padding-top:14px}}input,select{{font:inherit;padding:10px 14px;border:1px solid #cbd8d0;border-radius:6px;background:#fff}}.filters{{display:flex;flex-wrap:wrap;gap:10px}}footer{{font-size:11px;color:#74867b;margin-top:40px;overflow-wrap:anywhere}}[hidden]{{display:none}}@media(max-width:700px){{main{{padding:24px 16px}}h1{{font-size:29px}}.answers{{grid-template-columns:1fr}}header{{align-items:start}}}}
</style></head><body><main><header><div><div class="eyebrow">AI Quality Engineering / Experiment Report</div><h1>RAG Release Gate</h1><span class="muted">Baseline vs. candidate · reproducible quality evidence</span></div><span class="status">{status}</span></header>
<div class="meta"><div class="card"><span class="muted">Paired cases</span><b>{gate["case_count"]}</b></div><div class="card"><span class="muted">Evaluation engine</span><b>{html.escape(report["engine"])}</b></div><div class="card"><span class="muted">Candidate app p95</span><b>{gate["p95_latency_ms"]["candidate"]:.2f} ms</b></div><div class="card"><span class="muted">Release violations</span><b>{len(gate["violations"])}</b></div></div>
<div class="note">Builtin scores are literal fact, document ID, abstention, and token checks. Framework metrics are reported under their own names only after real SDK execution. Confidence intervals resample paired topic groups; these synthetic cases do not establish production effectiveness.</div>
<h2>Quality comparison</h2><div class="scroll"><table><thead><tr><th>Metric</th><th>Baseline</th><th>Candidate</th><th>Delta</th><th>Paired cases</th><th>95% delta CI</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
{"<h2>Release violations</h2><ul>" + violations + "</ul>" if violations else ""}
<h2>Case evidence</h2><div class="filters"><input id="search" placeholder="Search questions or answers" aria-label="Search cases"><select id="category" aria-label="Filter category"><option value="">All categories</option>{categories}</select><label><input id="imperfect" type="checkbox"> Only cases with a score below 1 or an error</label></div>{"".join(details)}
<footer>Created {html.escape(report["created_at"])}<br>Dataset SHA-256: {report["provenance"]["dataset_sha256"]}<br>Corpus SHA-256: {report["provenance"]["corpus_sha256"]}<br>Candidate: {html.escape(report["candidate_profile"])} · Full configuration, selected IDs, model settings and SDK versions are in report.json. Judge time is excluded from application latency.</footer></main><script>
function filter(){{const text=document.querySelector('#search').value.toLowerCase(),cat=document.querySelector('#category').value,imp=document.querySelector('#imperfect').checked;document.querySelectorAll('.case').forEach(el=>{{el.hidden=!(el.textContent.toLowerCase().includes(text)&&(!cat||el.dataset.category===cat)&&(!imp||el.dataset.imperfect==='true'));}});}}document.querySelectorAll('input,select').forEach(el=>el.addEventListener('input',filter));
</script></body></html>"""
    (output / "report.html").write_text(document, encoding="utf-8")
