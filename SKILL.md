---
name: proofline
description: Create polished, evidence-backed, self-contained HTML reports that are easy for people to read and straightforward for agents to parse. Use when the user asks to save, share, or present an audit, review, QA report, investigation, research brief, status record, postmortem, findings, or analysis as a browser-ready artifact. Supports index, signal, and essay visual modes plus an embedded machine-readable JSON block.
license: MIT
compatibility: Requires Python 3.9+ to use the bundled renderer; the workflow also works in agents that can author HTML directly.
metadata:
  version: "2.0.0"
  author: "Anish Giri"
  tags: "reports,audit,research,html,evidence,artifacts"
---

# Proofline

Turn source material into a decision document, not decorated prose.

The bundled renderer makes the common path deterministic: write one JSON
content file, run one command, inspect one HTML artifact. Keep the human view
and embedded JSON sourced from the same normalized data.

## Non-negotiable contract

- Deliver one `.html` file that opens from disk with no network connection.
- Put the decision or verdict before the supporting detail.
- Ground every factual claim in verbatim evidence or a measured value.
- Separate observed, inferred, and unverified work explicitly.
- Give each finding one stable ID, one severity, one location, and one next
  action when a fix is known.
- Never invent a score. Include one only when the report defines its rubric
  and the score is calculated from that rubric.
- Never mark an unverified claim `PASS`.
- Do not use placeholder copy, decorative charts, fake metrics, remote fonts,
  external scripts, or unrelated visual effects.
- Keep human findings and `#report-data` findings 1:1.

## Fast path

1. **Set the decision.** Reduce the request to one sentence: who needs this
   report, what they must decide, and what changed. Infer this from the source
   material; ask only when different interpretations would materially change
   the work.
2. **Build an evidence ledger.** For each intended claim, capture the exact
   quote or measured value, source location, confidence, and consequence.
   Discard claims that have neither evidence nor a clearly labeled hypothesis.
3. **Choose a visual mode.** Honor a user-specified style. Otherwise:
   - `index` — default decision record, audit, research brief, or mixed evidence.
   - `signal` — scored review, operational/security assessment, or a report
     that needs an immediate block/warn/pass signal.
   - `essay` — postmortem, technical narrative, research story, or long-form
     explanation where chronology and interpretation matter more than density.
4. **Write the content JSON.** Read
   [`references/schema.md`](references/schema.md) before the first report.
   Use [`examples/release-review.json`](examples/release-review.json) as a
   structural example, never as report content.
5. **Render.** From the installed skill directory, run:

   ```bash
   python scripts/proofline.py build report.json --output report.html
   ```

   Override automatic mode selection when needed:

   ```bash
   python scripts/proofline.py build report.json --output report.html --variant signal
   ```

6. **Inspect the artifact.** Open the HTML in a real browser. Check desktop
   and narrow mobile widths, keyboard focus, anchor navigation, long paths and
   code, empty states, print layout, and the browser console. Fix visible
   breakage before handoff.
7. **Validate independently when useful:**

   ```bash
   python scripts/proofline.py validate report.html --input report.json
   ```

   The `build` command runs the same structural checks before writing.
8. **Clean up.** Remove the temporary JSON unless the user asked to keep it.
   Return the saved HTML path and one sentence naming the report's decision.

## Content architecture

Use this order unless the user's subject demands a different narrative:

1. Masthead — title, subject, date, scope, author, method, sources.
2. Decision — concise label, headline, score only when justified, and next move.
3. Summary — three to six conclusions, not evidence repeated from findings.
4. Contents — generated from actual section titles.
5. Findings and analysis — one claim/finding per card with evidence, location,
   impact, and fix.
6. Verification — commands/scenarios actually run and explicit gaps.
7. Sources and footer — provenance, boundary, generated timestamp, and JSON
   pointer.

Keep most reports to three to seven sections. Split by reader question, not by
file, tool, or chronology unless chronology is the subject.

## Evidence and severity

Use only these severities:

| Severity | Meaning |
| --- | --- |
| `CRITICAL` | Data loss, security boundary failure, or the primary flow cannot be used. |
| `MAJOR` | A supported flow is broken or materially unreliable. |
| `MINOR` | Localized defect, regression risk, accessibility gap, or polish issue. |
| `NOTE` | Observation, limitation, inference, or claim awaiting confirmation. |
| `PASS` | A specific verified behavior that is worth preserving. |

Severity is never communicated by color alone. A claim with no direct evidence
is `NOTE`; name the check that would confirm or refute it. A `PASS` must name
the command, scenario, or observation that passed.

## Visual direction

Proofline is a report system, not a landing-page system.

- Make the hierarchy structural: oversized section numbers, a strict grid,
  hairline rules, and a visible trace from finding ID to evidence to action.
- Use one cool accent per mode plus fixed status colors. Reserve chroma for
  hierarchy and status.
- Use system sans for reading and system mono for IDs, paths, evidence,
  commands, dates, measurements, and table headings.
- Keep surfaces flat, corners square, and rules crisp. No gradients, glass,
  soft shadows, floating blobs, or ornamental charts.
- Use responsive type and fluid grids. Evidence must wrap; wide tables live in
  a labeled horizontal-scroll region.
- Reserve serif display type for `essay`; the other modes stay operational.
- Keep status labels visible in print and never rely on hover for information.

Choose the mode from the information shape, then vary scale and composition to
fit the subject. Do not paste a generic dashboard pattern onto every report.

## Quality gate

Do not call the report complete until all applicable checks pass:

- The file opens via `file://` with no failed external requests.
- The H1, decision, contents, findings, verification, sources, and footer are
  present and useful.
- Human finding IDs/count equal the embedded JSON.
- Every finding's evidence is verbatim, its location is exact, and its next
  action is specific when known.
- The browser console is clean; anchors resolve; no text or evidence clips.
- Desktop and narrow mobile layouts both remain readable.
- Print preview has a white background, visible severity words, and wrapped
  evidence.
- The JSON parses, contains no placeholders, and agrees with the visible text.
- The handoff names the saved path and any verification boundary.

## Failure modes

- **Too much source material:** rank by decision impact; keep the full evidence
  ledger available in the report only when it changes the decision.
- **Conflicting evidence:** surface the conflict as a `NOTE`; do not average it
  away or silently choose a side.
- **No findings:** say so, then show verified behavior and the examined
  boundary. Never imply a clean bill of health from an empty list alone.
- **No browser available:** run structural validation and state that visual
  inspection was not performed. Never claim a visual check that did not occur.
- **Huge evidence blocks:** preserve the relevant contiguous excerpt and add a
  visible truncation marker with the full source location.

## Bundled resources

- `references/schema.md` — content model and authoring rules; read when writing
  the first report or extending the renderer.
- `references/visual-system.md` — compact mode and layout guidance; read when
  choosing or adjusting a visual treatment.
- `scripts/proofline.py` — dependency-free renderer and validator.
- `examples/release-review.json` — example input shape only.
***
