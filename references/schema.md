# Proofline report schema

The renderer accepts one UTF-8 JSON object and produces one self-contained HTML
file. JSON is the content source of truth; the visible report is a rendering of
that data.

## Minimal input

```json
{
  "title": "Release readiness",
  "scope": "Version 2.4 checkout and payment paths",
  "method": "Static review plus targeted smoke tests",
  "summary": ["The release is not ready until the payment retry path is fixed."],
  "sections": [
    {
      "id": "decision-context",
      "title": "Decision context",
      "paragraphs": ["The release candidate changed the payment retry behavior."]
    }
  ],
  "findings": [
    {
      "id": "PAY-01",
      "severity": "MAJOR",
      "title": "Retry duplicates a capture",
      "observation": "A retried request can create a second capture.",
      "evidence": "observed response: status=201, capture_id=cap_92",
      "location": "src/payments/capture.ts:84",
      "section": "Payments",
      "impact": "A transient network failure can charge the customer twice.",
      "fix": "Pass the original idempotency key through the retry path.",
      "confidence": "high"
    }
  ]
}
```

`subject`, `date`, `author`, `sources`, `verdict`, `verification`, `stats`, and
`variant` are optional. `date` defaults to today and `author` defaults to
`Coding agent`.

## Top-level fields

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `title` | string | yes | Direct decision-oriented title, not a generic label. |
| `subject` | string | no | Compact subject shown in the masthead; defaults to `title`. |
| `scope` | string | yes | Exact system, product, path, period, or population examined. |
| `method` | string | yes | Concrete review, measurement, or interview method. |
| `date` | ISO date string | no | Report date; defaults to the render date. |
| `author` | string | no | Human or agent responsible for the record. |
| `sources` | string[] | no | URLs, file paths, commands, interviews, or datasets. |
| `variant` | `index`, `signal`, `essay` | no | Defaults to `signal` for critical/major findings, otherwise `index`. |
| `verdict` | object | no | Decision summary; see below. |
| `summary` | string[] | yes | Three to six concise conclusions; evidence belongs in findings. |
| `sections` | object[] | no | Three to seven reader-centered sections in display order. |
| `findings` | object[] | no | Findings in reading priority order. |
| `verification` | object | no | Commands/scenarios observed and explicit gaps. |
| `stats` | object | no | Scalar labels and values; no decorative metrics. |

## Verdict

```json
{
  "label": "BLOCK RELEASE",
  "headline": "Duplicate capture remains reproducible on the supported retry path.",
  "next": "Fix idempotency propagation and rerun the retry scenario.",
  "score": 62,
  "max": 100
}
```

`label` and `headline` are required when `verdict` exists. `next` is optional.
Omit `score` and `max` unless the report states and applies a real rubric.

## Sections

```json
{
  "id": "payments",
  "title": "Payments",
  "paragraphs": ["Analysis in chronological or decision order."],
  "table": {
    "columns": ["Case", "Expected", "Observed"],
    "rows": [["Retry after timeout", "One capture", "Two captures"]]
  },
  "finding_ids": ["PAY-01"]
}
```

- `id` is normalized to a URL-safe fragment. Supply a stable readable ID.
- `title` is required.
- `paragraphs` and `finding_ids` default to empty lists.
- `table` is optional. Every row must have exactly one cell per column.
- A finding may appear in only one section. Unassigned findings are placed in an
  automatically appended **Findings** section.
- The renderer creates an empty **Details** section when none are supplied.

## Findings

| Field | Type | Required | Rules |
| --- | --- | --- | --- |
| `id` | string | yes | Stable, unique, readable in isolation. |
| `severity` | enum | yes | `CRITICAL`, `MAJOR`, `MINOR`, `NOTE`, or `PASS`. |
| `title` | string | yes | Names the behavior or decision at stake. |
| `observation` | string | yes | One precise factual sentence. |
| `evidence` | string | yes | Verbatim excerpt, command output, or measured value. |
| `location` | string | yes | Exact file:line, URL, route, selector, interview timestamp, or dataset field. |
| `section` | string | yes | Subject area shown in the report context. |
| `impact` | string | no | Concrete user, operator, or business consequence. |
| `fix` | string | no | Specific next action with an exact target when known. |
| `confidence` | enum | no | `high`, `medium`, or `low`; defaults to `high`. |

`evidence` must be verbatim. Do not turn an inference into evidence. If no
direct evidence exists, use severity `NOTE` and say what would confirm it.

## Verification

```json
{
  "ran": [
    "npm test -- payment-retry — 18 passed, 1 failed",
    "Opened /checkout at 390px and 1440px — no clipping observed"
  ],
  "not_verified": [
    "Live PSP sandbox replay was unavailable",
    "Safari print preview was not inspected"
  ]
}
```

Describe only work actually performed. A command name without its result is not
verification. Keep skipped, unavailable, inferred, or uninspected work in
`not_verified`.

## Stats

Stats are optional scalar facts:

```json
{
  "findings": 3,
  "critical": 1,
  "verified_cases": 12,
  "coverage": "4/5 supported browsers"
}
```

Do not add a score, percentage, or count unless the source supports it.

## Validation behavior

`build` rejects unknown variants, invalid severities, missing required text,
duplicate finding IDs, repeated findings across sections, malformed tables,
invalid scores, placeholder narrative, external-capable HTML elements, duplicate
IDs, broken anchors, and a JSON block that disagrees with normalized input.

`validate` repeats the HTML checks and compares the embedded machine record to
the source JSON. It does not replace visual browser inspection or a print check.
