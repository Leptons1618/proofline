# Proofline

> Evidence-backed reports that look sharp, open anywhere, and stay machine-readable.

Proofline is an Agent Skill for turning audits, reviews, QA passes, research,
investigations, postmortems, and status records into polished, self-contained
HTML reports. Each artifact is designed for two readers at once:

- **People** get a decisive, evidence-led document that is comfortable to scan
  and read on desktop, mobile, or paper.
- **Agents** get the same content in an embedded `#report-data` JSON block—never
  a separately maintained copy that can drift.

The repository includes a dependency-free Python renderer, so the common path is
one content file and one command.

## Why Proofline

| Problem | Proofline answer |
| --- | --- |
| Generic, card-heavy report output | Three opinionated visual modes selected by information shape |
| Claims without inspectable proof | Verbatim evidence and exact locations are required |
| “Verified” work hidden in prose | Observed and unverified boundaries are always separated |
| Human report and agent data drifting apart | Both render from one normalized JSON source |
| Repeated hand-built HTML and CSS | One renderer creates responsive, print-aware artifacts |
| Agent-specific setup | Open Agent Skills format works across 80+ supported agents |

## Visual modes

### `index` — decision record

Cool white, ultramarine trace, dense sans/mono hierarchy. The default for audits,
research briefs, status records, and mixed evidence.

### `signal` — operational review

Near-black, cyan trace, high-contrast decision band. For release, operational,
security, and scored reviews where block/warn/pass state must be immediate.

### `essay` — technical narrative

Cool gray, restrained burgundy trace, serif display headings. For postmortems,
research stories, and chronology-led explanations.

All modes are responsive, keyboard navigable, print-aware, and free of external
assets, webfonts, scripts, CDNs, and runtime dependencies.

## Install

Proofline uses the open Agent Skills format. The cross-agent installer detects
installed agents and writes to the correct skill directories.

### Interactive install

```bash
npx skills add Leptons1618/proofline
```

Choose the agents and project/global scope when prompted.

### Install globally for selected agents

```bash
npx skills add Leptons1618/proofline \
  --global \
  --agent claude-code \
  --agent codex \
  --agent cursor \
  --agent opencode \
  --agent github-copilot \
  --yes
```

Use `--copy` if the agent's skill directory cannot use a symlink. Omit
`--global` to install into the current project and commit it with your team.

### One command for all detected agents

```bash
npx skills add Leptons1618/proofline --all --yes
```

### Use without installing

```bash
npx skills use Leptons1618/proofline
npx skills use Leptons1618/proofline --agent opencode
```

## Agent-specific paths

The installer is recommended. If your agent requires a manual copy, clone the
repository and place `SKILL.md` plus the supporting directories in its skill
directory.

| Agent | Project path | Global path |
| --- | --- | --- |
| Claude Code | `.claude/skills/proofline/` | `~/.claude/skills/proofline/` |
| Codex | `.agents/skills/proofline/` | `~/.codex/skills/proofline/` |
| Cursor | `.agents/skills/proofline/` | `~/.cursor/skills/proofline/` |
| OpenCode | `.agents/skills/proofline/` | `~/.config/opencode/skills/proofline/` |
| GitHub Copilot | `.agents/skills/proofline/` | `~/.copilot/skills/proofline/` |
| Gemini CLI | `.agents/skills/proofline/` | `~/.gemini/skills/proofline/` |
| Windsurf | `.windsurf/skills/proofline/` | `~/.codeium/windsurf/skills/proofline/` |
| Cline / Kilo / Roo universal path | `.agents/skills/proofline/` | `~/.agents/skills/proofline/` |

For a manual Git install:

```bash
git clone https://github.com/Leptons1618/proofline.git \
  .claude/skills/proofline
```

Restart the agent or start a new session after installing. The exact loading
behavior remains agent-specific; the open format is portable, not a promise that
every product hot-reloads skills.

## Use the skill

Ask the agent for a report artifact in natural language:

```text
Create a Proofline report from this audit. Save it as release-readiness.html.
Use the signal mode and show exactly what was and was not verified.
```

The skill activates for requests such as:

- “Save this review as a shareable HTML report.”
- “Turn the investigation into a polished report.”
- “Create a QA artifact with evidence and exact file locations.”
- “Make a client-ready research brief that still works for agents.”
- “Write a postmortem and save it as one self-contained HTML file.”

## Use the renderer directly

The renderer requires Python 3.9+ and no third-party packages.

```bash
python scripts/proofline.py build examples/release-review.json \
  --output report.html
```

Choose a visual mode explicitly:

```bash
python scripts/proofline.py build report-data.json \
  --output report.html \
  --variant essay
```

Validate a generated artifact against its source:

```bash
python scripts/proofline.py validate report.html --input report-data.json
```

The validator checks:

- one H1, valid viewport, and no external-capable resource tags;
- one `application/json` `#report-data` block;
- valid JSON with exact normalized-input parity;
- stable, unique section and finding IDs;
- human finding order matching machine finding order;
- resolved internal anchors; and
- no placeholder narrative.

Structural validation does not replace visual inspection. Open the report in a
browser, check narrow and wide layouts, inspect print preview, and read the
console before delivery.

## Content model

Start with the compact example, then consult the full schema:

- [`examples/release-review.json`](examples/release-review.json) — complete
  example input
- [`references/schema.md`](references/schema.md) — all fields, severities, and
  validation rules
- [`references/visual-system.md`](references/visual-system.md) — visual grammar,
  responsive behavior, print rules, and anti-patterns

The source object supports:

```json
{
  "title": "Release readiness",
  "scope": "RC3 on supported checkout paths",
  "method": "Source review and browser smoke test",
  "summary": ["One decision-focused conclusion."],
  "verdict": {
    "label": "BLOCK RELEASE",
    "headline": "The primary supported flow is not ready.",
    "next": "Fix the failing path and rerun the scenario."
  },
  "sections": [],
  "findings": [],
  "verification": {
    "ran": [],
    "not_verified": []
  }
}
```

## Output contract

Every generated report includes:

1. a provenance masthead;
2. a decision or conclusion first;
3. a short summary;
4. a linked contents index;
5. evidence-led sections and findings;
6. explicit observed/not-verified boundaries;
7. print-aware responsive CSS; and
8. a machine-readable JSON block that agrees with the visible report 1:1.

No claim is marked `PASS` without a named verification. No score is emitted
unless the report supplies and applies a real rubric.

## skills.sh discovery

Proofline is discoverable on [skills.sh](https://skills.sh/) through the open
skills ecosystem. skills.sh has no manual registry submission: a public skill
repository appears through install/discovery telemetry after the skill is
installed with the CLI.

Force a discovery/install event after pushing a revision:

```bash
npx skills add Leptons1618/proofline --list
```

Then install it normally so skills.sh can record the event:

```bash
npx skills add Leptons1618/proofline --skill proofline --yes
```

Canonical skill page:

<https://skills.sh/Leptons1618/proofline/proofline>

Directory indexing is asynchronous. A missing page immediately after the first
install is not a malformed skill; use the canonical URL once the directory has
processed the event.

## Security and privacy

Proofline's renderer:

- reads one local JSON file;
- writes one local HTML file;
- uses only the Python standard library;
- makes no network requests;
- embeds no external assets; and
- does not execute report content.

Review skills before installing them, especially when a source includes scripts.
The generated HTML remains inert: its only `<script>` is JSON.

## Repository layout

```text
proofline/
├── SKILL.md
├── scripts/
│   └── proofline.py
├── references/
│   ├── schema.md
│   └── visual-system.md
├── examples/
│   ├── release-review.json
│   └── release-review.html
├── LICENSE
└── README.md
```

## License

MIT. See [`LICENSE`](LICENSE).
