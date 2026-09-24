# Proofline visual system

Read this when selecting or adjusting a report mode. The renderer implements the
system; the mode should follow the information, not the trend.

## Shared visual grammar

Proofline treats the report as an evidence instrument:

- A strict top rule and metadata ledger establish provenance.
- Oversized section numerals make scanning positional.
- Findings follow a visible trace: stable ID → location → evidence → next move.
- Square corners, flat color, and hairline rules keep the artifact credible.
- Mono type marks data-shaped text: IDs, paths, commands, evidence, dates,
  measurements, and status.
- One cool accent carries hierarchy. Fixed status colors carry severity.
- The page is quiet until the reader reaches a finding, decision, or evidence
  block. There is no decorative “hero.”

## Choose a mode

### Index

Default for audits, research briefs, status records, and mixed evidence.

- Cool white ground with an ultramarine trace.
- Dense three-column summary on desktop; one column on mobile.
- Sans display and reading face, mono utility face.
- Best when the reader needs orientation before detail.

### Signal

Use for operational, security, release, or scored reviews.

- Near-black ground with a cyan trace.
- High-contrast decision band and strong finding labels.
- Sans display and reading face, mono utility face.
- Best when block/warn/pass state must be immediate.
- Print always switches to white paper and retains severity words.

### Essay

Use for postmortems, technical narratives, research stories, and chronology.

- Cool gray paper with a restrained burgundy trace.
- Serif display headings, sans reading text, mono evidence.
- Wide reading measure and strong chronological sections.
- Best when interpretation and narrative order carry more weight than density.

## Composition rules

1. Put the verdict in the first viewport when the report supports one.
2. Keep the summary to conclusions. Move proof into findings.
3. Use three to seven sections organized around reader questions.
4. Order findings by consequence and confidence, not discovery order.
5. Keep one accent line or mark as the signature. Remove competing ornaments.
6. Let long content create density naturally; do not shrink type to compensate.
7. Use tables only for genuinely comparable data.
8. Keep evidence blocks contiguous and preserve source location outside them.
9. Give negative space around decisions and findings; dense utilities may sit
   closer together.

## Responsive and print behavior

- At narrow widths, metadata, summary, contents, decision, and verification
  collapse in that order.
- Finding rail becomes a horizontal trace instead of squeezing content.
- Evidence wraps by default; tables scroll in a keyboard-focusable region.
- Long URLs and paths break without clipping.
- Print removes navigation, flattens tinted surfaces, forces a white background,
  and avoids breaking a finding card across pages.
- The severity word is always present; color is never the sole signal.

## Anti-patterns

- Generic hero sections, glass panels, gradient backgrounds, floating blobs.
- A dashboard card for every sentence.
- Severity represented only by red/amber/green chips.
- Fake scores, percentages, charts, or decorative data.
- Tiny mono text below 12px.
- Full-page screenshots instead of readable evidence excerpts.
- Warm cream + terracotta + serif used for every technical report.
- Repeating the same narrative in summary, section prose, and finding cards.
