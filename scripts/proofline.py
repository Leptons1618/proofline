#!/usr/bin/env python3
"""Render and validate Proofline self-contained HTML reports."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from string import Template
from typing import Any

SEVERITIES = ("CRITICAL", "MAJOR", "MINOR", "NOTE", "PASS")
VARIANTS = ("index", "signal", "essay")
FORBIDDEN_TAGS = {
    "link",
    "iframe",
    "object",
    "embed",
    "img",
    "picture",
    "source",
    "video",
    "audio",
}
PLACEHOLDER = re.compile(r"\b(?:lorem ipsum|tbd|todo|placeholder)\b", re.I)


class ReportError(ValueError):
    """Raised when report input or HTML violates the Proofline contract."""


def text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReportError(f"{field} must be a non-empty string")
    return value.strip()


def string_list(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    if value is None and allow_empty:
        return []
    if not isinstance(value, list):
        raise ReportError(f"{field} must be a list of strings")
    result = [text(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if not allow_empty and not result:
        raise ReportError(f"{field} must contain at least one item")
    return result


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return result or "section"


def unique_slug(value: str, used: set[str]) -> str:
    base = slug(value)
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def normalize_table(value: Any, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ReportError(f"{field} must be an object or null")
    columns = string_list(value.get("columns"), f"{field}.columns")
    rows = value.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ReportError(f"{field}.rows must be a non-empty list")
    normalized_rows: list[list[str]] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(columns):
            raise ReportError(
                f"{field}.rows[{row_index}] must contain {len(columns)} cells"
            )
        normalized_rows.append(
            [
                cell if isinstance(cell, str) else str(cell)
                for cell in row
            ]
        )
    return {"columns": columns, "rows": normalized_rows}


def normalize(data: Any, variant_override: str | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ReportError("report input must be a JSON object")

    variant = variant_override or data.get("variant") or "auto"
    if variant == "auto":
        severities = {
            str(item.get("severity", "")).upper()
            for item in data.get("findings", [])
            if isinstance(item, dict)
        }
        variant = "signal" if severities.intersection({"CRITICAL", "MAJOR"}) else "index"
    if variant not in VARIANTS:
        raise ReportError(f"variant must be one of: {', '.join(VARIANTS)}")

    normalized_findings: list[dict[str, Any]] = []
    finding_ids: set[str] = set()
    for index, finding in enumerate(data.get("findings", [])):
        field = f"findings[{index}]"
        if not isinstance(finding, dict):
            raise ReportError(f"{field} must be an object")
        finding_id = text(finding.get("id"), f"{field}.id")
        if finding_id in finding_ids:
            raise ReportError(f"duplicate finding id: {finding_id}")
        finding_ids.add(finding_id)
        severity = text(finding.get("severity"), f"{field}.severity").upper()
        if severity not in SEVERITIES:
            raise ReportError(
                f"{field}.severity must be one of: {', '.join(SEVERITIES)}"
            )
        normalized_findings.append(
            {
                "id": finding_id,
                "severity": severity,
                "title": text(finding.get("title"), f"{field}.title"),
                "observation": text(
                    finding.get("observation"), f"{field}.observation"
                ),
                "evidence": text(finding.get("evidence"), f"{field}.evidence"),
                "location": text(finding.get("location"), f"{field}.location"),
                "section": text(finding.get("section"), f"{field}.section"),
                "impact": text(finding.get("impact", ""), f"{field}.impact")
                if finding.get("impact")
                else "",
                "fix": text(finding.get("fix", ""), f"{field}.fix")
                if finding.get("fix")
                else "",
                "confidence": text(
                    finding.get("confidence", "high"), f"{field}.confidence"
                ).lower(),
            }
        )
        if normalized_findings[-1]["confidence"] not in {
            "high",
            "medium",
            "low",
        }:
            raise ReportError(f"{field}.confidence must be high, medium, or low")

    normalized_sections: list[dict[str, Any]] = []
    used_section_ids: set[str] = set()
    used_findings: set[str] = set()
    for index, section in enumerate(data.get("sections", [])):
        field = f"sections[{index}]"
        if not isinstance(section, dict):
            raise ReportError(f"{field} must be an object")
        section_id = unique_slug(
            text(section.get("id", f"section-{index + 1}"), f"{field}.id"),
            used_section_ids,
        )
        section_finding_ids = string_list(
            section.get("finding_ids", []), f"{field}.finding_ids", allow_empty=True
        )
        for finding_id in section_finding_ids:
            if finding_id not in finding_ids:
                raise ReportError(
                    f"{field}.finding_ids references unknown finding {finding_id}"
                )
            if finding_id in used_findings:
                raise ReportError(f"finding {finding_id} appears in multiple sections")
            used_findings.add(finding_id)
        normalized_sections.append(
            {
                "id": section_id,
                "title": text(section.get("title"), f"{field}.title"),
                "paragraphs": string_list(
                    section.get("paragraphs", []),
                    f"{field}.paragraphs",
                    allow_empty=True,
                ),
                "table": normalize_table(section.get("table"), f"{field}.table"),
                "finding_ids": section_finding_ids,
            }
        )

    orphan_findings = [item["id"] for item in normalized_findings if item["id"] not in used_findings]
    if orphan_findings:
        normalized_sections.append(
            {
                "id": unique_slug("findings", used_section_ids),
                "title": "Findings",
                "paragraphs": [],
                "table": None,
                "finding_ids": orphan_findings,
            }
        )
    if not normalized_sections:
        normalized_sections.append(
            {
                "id": "details",
                "title": "Details",
                "paragraphs": [],
                "table": None,
                "finding_ids": [],
            }
        )

    verdict_value = data.get("verdict")
    verdict: dict[str, Any] | None = None
    if verdict_value is not None:
        if not isinstance(verdict_value, dict):
            raise ReportError("verdict must be an object or null")
        verdict = {
            "label": text(verdict_value.get("label"), "verdict.label"),
            "headline": text(verdict_value.get("headline"), "verdict.headline"),
            "next": text(verdict_value.get("next", ""), "verdict.next")
            if verdict_value.get("next")
            else "",
            "score": verdict_value.get("score"),
            "max": verdict_value.get("max", 100),
        }
        for key in ("score", "max"):
            value = verdict[key]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ReportError(f"verdict.{key} must be numeric")
        if verdict["score"] < 0 or verdict["max"] <= 0 or verdict["score"] > verdict["max"]:
            raise ReportError("verdict score must be between zero and max")

    verification_value = data.get("verification", {})
    if not isinstance(verification_value, dict):
        raise ReportError("verification must be an object")
    verification = {
        "ran": string_list(
            verification_value.get("ran", []),
            "verification.ran",
            allow_empty=True,
        ),
        "not_verified": string_list(
            verification_value.get("not_verified", []),
            "verification.not_verified",
            allow_empty=True,
        ),
    }

    stats_value = data.get("stats", {})
    if not isinstance(stats_value, dict):
        raise ReportError("stats must be an object")
    stats: dict[str, str | int | float | bool] = {}
    for key, value in stats_value.items():
        if not isinstance(key, str) or not key.strip():
            raise ReportError("stats keys must be non-empty strings")
        if not isinstance(value, (str, int, float, bool)):
            raise ReportError("stats values must be strings, numbers, or booleans")
        stats[key] = value

    return {
        "schemaVersion": 1,
        "title": text(data.get("title"), "title"),
        "subject": text(data.get("subject", data.get("title")), "subject"),
        "date": text(data.get("date", date.today().isoformat()), "date"),
        "scope": text(data.get("scope"), "scope"),
        "author": text(data.get("author", "Coding agent"), "author"),
        "method": text(data.get("method"), "method"),
        "sources": string_list(data.get("sources", []), "sources", allow_empty=True),
        "variant": variant,
        "verdict": verdict,
        "summary": string_list(data.get("summary"), "summary"),
        "sections": normalized_sections,
        "findings": normalized_findings,
        "verification": verification,
        "stats": stats,
    }


def is_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value, re.I))


def render_location(value: str) -> str:
    safe = escape(value)
    if is_url(value):
        return f'<a href="{safe}" rel="noreferrer noopener">{safe}</a>'
    return f"<code>{safe}</code>"


def render_paragraphs(paragraphs: list[str]) -> str:
    return "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def render_table(table: dict[str, Any]) -> str:
    headings = "".join(f"<th scope=\"col\">{escape(item)}</th>" for item in table["columns"])
    rows = []
    for row in table["rows"]:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row)
        rows.append(f"<tr>{cells}</tr>")
    return (
        '<div class="table-scroll" role="region" aria-label="Scrollable data table" tabindex="0">'
        f"<table><thead><tr>{headings}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        "</div>"
    )


def render_finding(finding: dict[str, Any], index: int) -> str:
    severity = finding["severity"]
    location = render_location(finding["location"])
    evidence = escape(finding["evidence"])
    impact = (
        f'<div class="finding-row"><span>Impact</span><p>{escape(finding["impact"])}</p></div>'
        if finding["impact"]
        else ""
    )
    fix = (
        f'<div class="fix"><strong>Next:</strong> {escape(finding["fix"])}</div>'
        if finding["fix"]
        else '<div class="fix unknown"><strong>Next:</strong> Confirm the proposed action before implementation.</div>'
    )
    return f"""<article class="finding severity-{severity.lower()}" id="finding-{index + 1}-{slug(finding['id'])}" data-finding-id="{escape(finding['id'])}">
  <div class="finding-rail"><span>{escape(finding['id'])}</span><i aria-hidden="true"></i></div>
  <div class="finding-body">
    <header class="finding-head">
      <span class="severity">{escape(severity)}</span>
      <span class="confidence">{escape(finding['confidence'])} confidence</span>
    </header>
    <h3>{escape(finding['title'])}</h3>
    <p class="observation">{escape(finding['observation'])}</p>
    <div class="finding-row location"><span>Location</span><div>{location}</div></div>
    {impact}
    <div class="evidence"><span>Evidence · verbatim</span><pre><code>{evidence}</code></pre></div>
    {fix}
  </div>
</article>"""


def render_html(data: dict[str, Any]) -> str:
    findings_by_id = {item["id"]: item for item in data["findings"]}
    title = escape(data["title"])
    subject = escape(data["subject"])
    summary = "".join(
        f'<article class="summary-card"><span>{index:02d}</span><p>{escape(item)}</p></article>'
        for index, item in enumerate(data["summary"], start=1)
    )

    contents = "".join(
        f'<li><a href="#{escape(section["id"])}"><span>{index:02d}</span>{escape(section["title"])}</a></li>'
        for index, section in enumerate(data["sections"], start=1)
    )

    section_html: list[str] = []
    for section_index, section in enumerate(data["sections"], start=1):
        blocks = [render_paragraphs(section["paragraphs"])]
        if section["table"]:
            blocks.append(render_table(section["table"]))
        for finding_id in section["finding_ids"]:
            finding_index = next(
                index for index, item in enumerate(data["findings"]) if item["id"] == finding_id
            )
            blocks.append(render_finding(findings_by_id[finding_id], finding_index))
        section_html.append(
            f'<section class="report-section" id="{escape(section["id"])}" data-section-id="{escape(section["id"])}" aria-labelledby="{escape(section["id"])}-title">'
            f'<header class="section-head"><span class="section-number">{section_index:02d}</span>'
            f'<div><p>Section {section_index:02d}</p><h2 id="{escape(section["id"])}-title">{escape(section["title"])}</h2></div></header>'
            f'<div class="section-body">{"".join(blocks)}</div></section>'
        )

    verdict_html = ""
    if data["verdict"]:
        verdict = data["verdict"]
        score = ""
        if verdict["score"] is not None:
            score = (
                f'<div class="score"><strong>{escape(str(verdict["score"]))}</strong>'
                f'<span>/ {escape(str(verdict["max"]))}</span></div>'
            )
        next_move = (
            f'<p class="next"><span>Next</span>{escape(verdict["next"])}</p>'
            if verdict["next"]
            else ""
        )
        verdict_html = f"""<section class="decision" aria-labelledby="decision-title">
  <div class="decision-label"><p>Decision</p><h2 id="decision-title">{escape(verdict['label'])}</h2></div>
  <div class="decision-copy"><p>{escape(verdict['headline'])}</p>{next_move}</div>
  {score}
</section>"""

    verification = data["verification"]
    verification_html = ""
    if verification["ran"] or verification["not_verified"]:
        ran = "".join(f"<li>{escape(item)}</li>" for item in verification["ran"])
        missing = "".join(
            f"<li>{escape(item)}</li>" for item in verification["not_verified"]
        )
        empty_ran = '<li class="empty">No executable verification was supplied.</li>' if not ran else ""
        empty_missing = '<li class="empty">No known verification gaps.</li>' if not missing else ""
        verification_html = f"""<section class="verification" aria-labelledby="verification-title">
  <header><span>Boundary</span><h2 id="verification-title">Verification record</h2></header>
  <div class="verification-grid">
    <div><h3><i class="pass-dot" aria-hidden="true"></i>Observed</h3><ul>{ran or empty_ran}</ul></div>
    <div><h3><i class="note-dot" aria-hidden="true"></i>Not verified</h3><ul>{missing or empty_missing}</ul></div>
  </div>
</section>"""

    sources = "".join(
        f"<li>{render_location(source)}</li>" for source in data["sources"]
    )
    sources_html = (
        f'<section class="sources" aria-labelledby="sources-title"><h2 id="sources-title">Sources</h2><ol>{sources}</ol></section>'
        if sources
        else ""
    )

    stats_html = ""
    if data["stats"]:
        stats = "".join(
            f"<div><dt>{escape(str(key))}</dt><dd>{escape(str(value))}</dd></div>"
            for key, value in data["stats"].items()
        )
        stats_html = f'<dl class="stats">{stats}</dl>'

    metadata = [
        ("Date", data["date"]),
        ("Scope", data["scope"]),
        ("Author", data["author"]),
        ("Method", data["method"]),
    ]
    meta_html = "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>"
        for label, value in metadata
    )
    machine_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )

    return Template(
        """<!doctype html>
<html lang="en" class="variant-${variant}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>${title}</title>
  <style>${css}</style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to report</a>
  <header class="masthead">
    <div class="masthead-mark" aria-hidden="true"><span>P</span><i></i><i></i></div>
    <div class="masthead-title"><p class="kicker">Proofline · ${subject}</p><h1>${title}</h1></div>
    <dl class="metadata">${meta_html}</dl>
  </header>
  <main id="main">
    ${verdict_html}
    <section class="summary" aria-labelledby="summary-title">
      <header><span>Brief</span><h2 id="summary-title">What matters</h2></header>
      <div class="summary-grid">${summary}</div>
      ${stats_html}
    </section>
    <nav class="contents" aria-label="Report contents"><p>Index</p><ol>${contents}</ol></nav>
    <div class="sections">${section_html}</div>
    ${verification_html}
    ${sources_html}
  </main>
  <footer><p><strong>Proofline</strong> · ${date} · ${method}</p><p>Machine record: <a href="#report-data">#report-data</a></p></footer>
  <script type="application/json" id="report-data">${machine_json}</script>
</body>
</html>"""
    ).safe_substitute(
        variant=escape(data["variant"]),
        title=title,
        subject=subject,
        css=CSS,
        date=escape(data["date"]),
        method=escape(data["method"]),
        meta_html=meta_html,
        verdict_html=verdict_html,
        summary=summary,
        stats_html=stats_html,
        contents=contents,
        section_html="".join(section_html),
        verification_html=verification_html,
        sources_html=sources_html,
        machine_json=machine_json,
    )


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.finding_ids: list[str] = []
        self.section_ids: list[str] = []
        self.scripts: list[dict[str, str]] = []
        self.forbidden: list[str] = []
        self.h1_count = 0
        self.has_viewport = False
        self._script: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        if tag == "h1":
            self.h1_count += 1
        if tag == "script":
            self._script = {"attrs": " ".join(f"{key}={value}" for key, value in attrs.items()), "text": ""}
        if tag in FORBIDDEN_TAGS:
            self.forbidden.append(tag)
        element_id = attrs.get("id")
        if element_id:
            self.ids.append(element_id)
        href = attrs.get("href", "")
        if href.startswith("#"):
            self.hrefs.append(href[1:])
        if "data-finding-id" in attrs:
            self.finding_ids.append(attrs["data-finding-id"])
        if "data-section-id" in attrs:
            self.section_ids.append(attrs["data-section-id"])
        if tag == "meta" and attrs.get("name") == "viewport":
            self.has_viewport = True

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script is not None:
            self.scripts.append(self._script)
            self._script = None


def validate_html(html_text: str, expected: dict[str, Any]) -> None:
    parser = ReportParser()
    parser.feed(html_text)
    errors: list[str] = []
    if not html_text.lstrip().lower().startswith("<!doctype html>"):
        errors.append("missing HTML5 doctype")
    if parser.h1_count != 1:
        errors.append(f"expected one h1, found {parser.h1_count}")
    if not parser.has_viewport:
        errors.append("missing viewport meta tag")
    if parser.forbidden:
        errors.append(f"forbidden external-capable tags: {', '.join(sorted(set(parser.forbidden)))}")
    if len(parser.scripts) != 1:
        errors.append(f"expected one JSON script, found {len(parser.scripts)}")
    elif (
        'type=application/json' not in parser.scripts[0]["attrs"]
        or "id=report-data" not in parser.scripts[0]["attrs"]
    ):
        errors.append("report-data script has wrong attributes")
    else:
        try:
            machine = json.loads(parser.scripts[0]["text"])
        except json.JSONDecodeError as exc:
            errors.append(f"report-data is invalid JSON: {exc}")
        else:
            if machine != expected:
                errors.append("report-data does not match normalized input")
    if len(parser.ids) != len(set(parser.ids)):
        errors.append("duplicate HTML ids detected")
    missing_anchors = sorted(set(parser.hrefs) - set(parser.ids))
    if missing_anchors:
        errors.append(f"unresolved anchors: {', '.join(missing_anchors)}")
    if parser.finding_ids != [item["id"] for item in expected["findings"]]:
        errors.append("human finding order/IDs do not match report-data")
    if parser.section_ids != [item["id"] for item in expected["sections"]]:
        errors.append("human section order/IDs do not match report-data")

    searchable = " ".join(
        [expected["title"], expected["subject"], *expected["summary"]]
        + [item["observation"] for item in expected["findings"]]
        + [paragraph for section in expected["sections"] for paragraph in section["paragraphs"]]
    )
    if PLACEHOLDER.search(searchable):
        errors.append("placeholder copy detected in narrative content")

    if errors:
        raise ReportError("; ".join(errors))


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ReportError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ReportError(f"invalid JSON in {path}: {exc}") from exc


def build(args: argparse.Namespace) -> int:
    data = normalize(load_json(Path(args.input)), args.variant)
    output = render_html(data)
    validate_html(output, data)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(output, encoding="utf-8", newline="\n")
    print(
        f"Built {destination} · {len(data['sections'])} sections · "
        f"{len(data['findings'])} findings · {data['variant']}"
    )
    return 0


def validate(args: argparse.Namespace) -> int:
    path = Path(args.report)
    try:
        html_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ReportError(f"report file not found: {path}") from exc
    expected = normalize(load_json(Path(args.input)), args.variant)
    validate_html(html_text, expected)
    print(
        f"Validated {path} · JSON agrees · {len(expected['findings'])} findings · "
        "self-contained structure valid"
    )
    return 0


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(
        prog="proofline.py", description="Build and validate Proofline reports"
    )
    commands = cli.add_subparsers(dest="command", required=True)
    build_parser = commands.add_parser("build", help="render report JSON to HTML")
    build_parser.add_argument("input", help="source JSON file")
    build_parser.add_argument("--output", "-o", required=True, help="destination HTML file")
    build_parser.add_argument("--variant", choices=VARIANTS, help="override visual mode")
    build_parser.set_defaults(handler=build)
    validate_parser = commands.add_parser("validate", help="validate HTML against source JSON")
    validate_parser.add_argument("report", help="generated HTML file")
    validate_parser.add_argument("--input", "-i", required=True, help="source JSON file")
    validate_parser.add_argument("--variant", choices=VARIANTS, help="override visual mode")
    validate_parser.set_defaults(handler=validate)
    return cli


def main() -> int:
    try:
        args = parser().parse_args()
        return args.handler(args)
    except ReportError as exc:
        print(f"proofline: {exc}", file=sys.stderr)
        return 2


CSS = r"""
:root{--bg:#f4f6fa;--surface:#fff;--surface-2:#e9edf4;--ink:#111827;--body:#344054;--muted:#5d6978;--line:#cbd3df;--line-strong:#7d8998;--accent:#2447d8;--accent-soft:#e8ecff;--crit:#a92734;--major:#8a4b08;--minor:#285ea8;--note:#4b5565;--pass:#087a4b;--sans:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;--serif:Georgia,"Times New Roman",serif;--mono:ui-monospace,"SFMono-Regular",Cascadia Code,Consolas,monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--bg)}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 var(--sans);text-rendering:optimizeLegibility}::selection{background:var(--accent);color:#fff}a{color:inherit;text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}:focus-visible{outline:3px solid var(--accent);outline-offset:4px}.skip-link{position:fixed;z-index:20;top:12px;left:12px;padding:10px 14px;background:var(--ink);color:var(--surface);transform:translateY(-180%)}.skip-link:focus{transform:none}
.masthead{display:grid;grid-template-columns:72px minmax(0,1fr) minmax(260px,34%);max-width:1240px;margin:0 auto;padding:40px 28px 34px;border-top:8px solid var(--accent);border-bottom:1px solid var(--line-strong);background:var(--surface)}.masthead-mark{position:relative;align-self:start;width:48px;height:62px;border:1px solid var(--ink);font:700 30px/60px var(--mono);text-align:center}.masthead-mark i{position:absolute;right:-8px;width:16px;height:16px;background:var(--bg);border:1px solid var(--line-strong)}.masthead-mark i:first-of-type{top:-8px}.masthead-mark i:last-of-type{bottom:-8px}.masthead-title{align-self:end;padding:0 32px}.kicker,.metadata dt,.decision p,.summary>header>span,.contents>p,.section-head p,.finding-head,.evidence>span,.finding-row>span,.verification header>span,.sources h2,.stats dt{font:700 11px/1.3 var(--mono);letter-spacing:.12em;text-transform:uppercase}.kicker{margin:0 0 16px;color:var(--accent)}h1{max-width:14ch;margin:0;font-size:clamp(44px,6.4vw,88px);line-height:.92;letter-spacing:-.065em}h2,h3,p{overflow-wrap:anywhere}.metadata{align-self:stretch;display:grid;grid-template-columns:1fr;margin:0;border-left:1px solid var(--line)}.metadata>div{display:grid;grid-template-columns:88px 1fr;gap:12px;padding:11px 0;border-bottom:1px solid var(--line)}.metadata>div:last-child{border-bottom:0}.metadata dt{color:var(--muted)}.metadata dd{margin:0;font:13px/1.45 var(--mono)}
main{display:block;max-width:1184px;margin:0 auto;padding:0 28px 80px}.decision{display:grid;grid-template-columns:minmax(180px,.6fr) minmax(0,1.4fr) auto;gap:32px;align-items:end;margin:56px 0;padding:28px;background:var(--ink);color:var(--surface);border-left:8px solid var(--accent)}.decision p{margin:0;color:var(--muted)}.decision h2{margin:8px 0 0;font:700 clamp(24px,3vw,42px)/1 var(--mono);letter-spacing:-.05em}.decision-copy>p{margin:0;color:var(--surface);font-size:clamp(20px,2.3vw,30px);line-height:1.2;letter-spacing:-.02em}.decision .next{display:grid;grid-template-columns:64px 1fr;gap:12px;margin-top:18px;color:var(--muted);font:14px/1.5 var(--sans);letter-spacing:0;text-transform:none}.decision .next span{color:var(--surface);font:700 11px/1.5 var(--mono);letter-spacing:.12em;text-transform:uppercase}.score{display:grid;min-width:110px;text-align:right}.score strong{font:700 clamp(44px,6vw,76px)/.8 var(--mono);letter-spacing:-.08em}.score span{font:13px var(--mono);color:var(--muted)}
.summary{margin:0 0 64px}.summary>header,.verification>header{display:grid;grid-template-columns:116px 1fr;align-items:end;margin-bottom:22px;padding-bottom:12px;border-bottom:2px solid var(--ink)}.summary>header>span,.verification header>span{color:var(--accent)}.summary h2,.verification h2{margin:0;font-size:30px;line-height:1;letter-spacing:-.035em}.summary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--line-strong);border-left:1px solid var(--line-strong)}.summary-card{min-height:154px;padding:20px;border-right:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong);background:var(--surface)}.summary-card span{display:block;margin-bottom:30px;color:var(--accent);font:700 12px var(--mono)}.summary-card p{margin:0;font-size:16px;line-height:1.45}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:24px 0 0;border:1px solid var(--line)}.stats>div{padding:14px;border-right:1px solid var(--line)}.stats dt{color:var(--muted)}.stats dd{margin:5px 0 0;font:700 24px var(--mono)}
.contents{display:grid;grid-template-columns:116px 1fr;gap:18px;margin:0 0 72px;padding:18px 0;border-top:1px solid var(--line-strong);border-bottom:1px solid var(--line-strong)}.contents>p{margin:4px 0 0;color:var(--muted)}.contents ol{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 32px;margin:0;padding:0;list-style:none}.contents a{display:grid;grid-template-columns:40px 1fr;gap:8px;padding:7px 0}.contents a span{color:var(--accent);font:12px var(--mono)}
.report-section{scroll-margin-top:20px;margin:0 0 88px}.section-head{display:grid;grid-template-columns:116px minmax(0,1fr);gap:18px;align-items:end;margin-bottom:28px;padding-bottom:16px;border-bottom:2px solid var(--ink)}.section-number{color:var(--accent);font:700 clamp(42px,6vw,76px)/.75 var(--mono);letter-spacing:-.08em}.section-head p{margin:0 0 6px;color:var(--muted)}.section-head h2{margin:0;font-size:clamp(28px,3.4vw,46px);line-height:1;letter-spacing:-.045em}.section-body{max-width:920px}.section-body>p{max-width:76ch;margin:0 0 18px;font-size:17px}.table-scroll{max-width:100%;margin:28px 0;overflow-x:auto;border:1px solid var(--line-strong);background:var(--surface)}table{width:100%;min-width:680px;border-collapse:collapse;font-size:14px}th,td{padding:13px 15px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:var(--ink);color:var(--surface);font:700 11px/1.3 var(--mono);letter-spacing:.08em;text-transform:uppercase}tr:last-child td{border-bottom:0}code,pre{font-family:var(--mono)}:not(pre)>code{font-size:.88em;background:var(--surface-2);padding:2px 5px;overflow-wrap:anywhere}
.finding{display:grid;grid-template-columns:88px minmax(0,1fr);margin-top:28px;border:1px solid var(--line-strong);background:var(--surface)}.finding-rail{display:flex;flex-direction:column;align-items:center;padding:20px 12px;border-right:1px solid var(--line);font:700 12px var(--mono);writing-mode:vertical-rl;transform:rotate(180deg)}.finding-rail i{width:1px;flex:1;margin-top:18px;background:var(--accent)}.finding-body{min-width:0;padding:24px}.finding-head{display:flex;gap:12px;align-items:center;margin-bottom:16px}.finding-head .severity{padding:5px 8px;border:1px solid currentColor;color:var(--note)}.finding-head .confidence{margin-left:auto;color:var(--muted);font-weight:400;letter-spacing:.06em}.severity-critical .severity{color:var(--crit);background:#fff0f1}.severity-major .severity{color:var(--major);background:#fff7e8}.severity-minor .severity{color:var(--minor);background:#edf5ff}.severity-pass .severity{color:var(--pass);background:#eaf8f1}.finding h3{margin:0 0 10px;font-size:22px;line-height:1.2;letter-spacing:-.025em}.observation{max-width:74ch;margin:0 0 22px;color:var(--body)}.finding-row{display:grid;grid-template-columns:90px minmax(0,1fr);gap:12px;padding:11px 0;border-top:1px solid var(--line)}.finding-row>span{padding-top:3px;color:var(--muted)}.finding-row p,.finding-row>div{margin:0;font:13px/1.55 var(--mono);overflow-wrap:anywhere}.evidence{margin-top:18px;border:1px solid var(--line-strong)}.evidence>span{display:block;padding:8px 12px;background:var(--ink);color:var(--surface)}.evidence pre{margin:0;padding:15px;overflow:auto;background:var(--surface-2);white-space:pre-wrap;word-break:break-word;font:13px/1.65 var(--mono)}.fix{margin-top:18px;padding:14px 16px;border-left:4px solid var(--accent);background:var(--accent-soft);font-size:14px}.fix.unknown{border-left-color:var(--note);background:var(--surface-2)}
.verification{margin:0 0 64px;padding:28px;background:var(--surface);border:1px solid var(--line-strong)}.verification-grid{display:grid;grid-template-columns:1fr 1fr;gap:32px}.verification h3{display:flex;align-items:center;gap:9px;margin:0 0 12px;font-size:16px}.verification h3 i{width:9px;height:9px;border-radius:50%}.pass-dot{background:var(--pass)}.note-dot{background:var(--major)}.verification ul{margin:0;padding-left:20px;color:var(--body)}.verification li+li{margin-top:8px}.verification li.empty{color:var(--muted);font-style:italic}.sources{margin:0 0 56px;padding-top:24px;border-top:1px solid var(--line-strong)}.sources h2{margin:0 0 14px;font-size:24px}.sources ol{margin:0;padding-left:24px}.sources li+li{margin-top:6px}footer{display:grid;grid-template-columns:1fr 1fr;gap:20px;max-width:1184px;margin:0 auto;padding:24px 28px 40px;border-top:1px solid var(--line-strong);color:var(--muted);font:12px/1.5 var(--mono)}footer p{margin:0}footer p:last-child{text-align:right}
.variant-signal{--bg:#080a0f;--surface:#10151d;--surface-2:#171e28;--ink:#f5f7fb;--body:#c0cad7;--muted:#8e9bad;--line:#303a49;--line-strong:#586577;--accent:#5ee7f5;--accent-soft:#12333a;--crit:#ff8090;--major:#ffc65c;--minor:#8ebcff;--note:#aab4c2;--pass:#68e5aa}.variant-signal .masthead-mark i{background:var(--bg)}.variant-signal .decision{border-left-color:var(--accent);background:#0d1219}.variant-signal .decision h2{color:var(--accent)}.variant-signal .summary-card,.variant-signal .finding,.variant-signal .verification{box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 10%,transparent)}.variant-signal .severity-critical .severity{background:#35151c}.variant-signal .severity-major .severity{background:#332510}.variant-signal .severity-minor .severity{background:#102744}.variant-signal .severity-pass .severity{background:#0d3325}.variant-signal .decision{box-shadow:none}
.variant-essay{--bg:#e9edef;--surface:#f8f9f8;--surface-2:#e1e6e8;--ink:#16191c;--body:#3c454c;--muted:#5d6870;--line:#bcc5ca;--line-strong:#77838a;--accent:#8f2639;--accent-soft:#f5e7ea}.variant-essay .masthead{border-top-width:10px}.variant-essay h1,.variant-essay .section-head h2,.variant-essay .summary h2,.variant-essay .verification h2{font-family:var(--serif);font-weight:400}.variant-essay h1{font-size:clamp(52px,7.5vw,104px);line-height:.88;letter-spacing:-.055em}.variant-essay .decision{border-left-width:10px}.variant-essay .decision h2{font-family:var(--serif);font-weight:400}.variant-essay .summary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.variant-essay .section-number{font-family:var(--serif);font-weight:400}.variant-essay .finding{border-left:6px solid var(--accent)}
@media(max-width:820px){.masthead{grid-template-columns:52px 1fr}.masthead-title{padding:0 0 0 20px}.metadata{grid-column:1/-1;grid-template-columns:repeat(2,1fr);margin-top:28px;border-left:0;border-top:1px solid var(--line)}.metadata>div{padding-right:16px}.decision{grid-template-columns:1fr}.score{text-align:left}.summary-grid,.variant-essay .summary-grid{grid-template-columns:1fr 1fr}.contents{grid-template-columns:1fr}.contents ol{grid-template-columns:1fr}.section-head{grid-template-columns:84px 1fr}.verification-grid{grid-template-columns:1fr}}
@media(max-width:560px){.masthead{padding:24px 18px}.masthead-mark{width:38px;height:52px;font-size:25px;line-height:50px}.masthead-title{padding-left:14px}h1{font-size:46px}.metadata{grid-template-columns:1fr}.metadata>div{grid-template-columns:82px 1fr}main{padding-inline:18px}.decision{margin-block:36px;padding:20px}.summary{margin-bottom:48px}.summary>header,.verification>header{grid-template-columns:1fr;gap:8px}.summary-grid,.variant-essay .summary-grid{grid-template-columns:1fr}.summary-card{min-height:0}.summary-card span{margin-bottom:16px}.contents{margin-bottom:56px}.report-section{margin-bottom:64px}.section-head{grid-template-columns:1fr}.section-number{font-size:48px}.finding{grid-template-columns:1fr}.finding-rail{height:auto;flex-direction:row;gap:12px;padding:10px 14px;border-right:0;border-bottom:1px solid var(--line);writing-mode:initial;transform:none}.finding-rail i{width:auto;height:1px;margin:0}.finding-body{padding:18px}.finding-row{grid-template-columns:1fr;gap:5px}.verification{padding:20px}.verification-grid{gap:24px}footer{grid-template-columns:1fr;padding-inline:18px}footer p:last-child{text-align:left}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{@page{margin:14mm}html,body{background:#fff!important;color:#111!important;font-size:10.5pt}.skip-link,.masthead-mark{display:none}.masthead{max-width:none;padding:0 0 18pt;border-top:5pt solid #111;border-bottom:1pt solid #777;background:#fff}.masthead-title{padding:0}.masthead h1{font-size:34pt}.metadata{color:#222}.decision{grid-template-columns:.55fr 1.25fr auto;margin:24pt 0;padding:16pt;background:#fff;color:#111;border:1pt solid #111}.decision p,.decision-copy>p,.decision .next span,.score span{color:#222!important}.score{min-width:72pt}.summary{margin-bottom:28pt}.summary-grid{grid-template-columns:repeat(3,1fr)}.report-section{margin-bottom:36pt}.finding,.verification,.table-scroll{background:#fff;color:#111;box-shadow:none!important;break-inside:avoid}.finding-body{padding:14pt}.evidence{background:#fff}.evidence>span{background:#eee;color:#111}.fix{background:#f2f2f2}.contents{display:none}footer{max-width:none;color:#222}a{color:#111}}
"""


if __name__ == "__main__":
    raise SystemExit(main())
