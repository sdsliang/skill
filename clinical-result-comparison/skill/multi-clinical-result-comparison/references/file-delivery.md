# File Deliverable Contract (v0.9)

## Purpose

The finished consumer-facing report is delivered as a **workspace file** presented through the Tool Smith `present_artifact` capability, not as streamed chat text. This lets the backend serve the file directly (no parsing of model output), prevents uncontrolled intro text or trailing tool calls, and gives the report a stable, downloadable, shareable form.

## Deployment requirements

- The project must have the **`artifact_presentation`** capability enabled (per-project switch, default OFF) for `present_artifact` to be visible to the root agent.
- The **`visualization`** capability must also be enabled for `::visualization[...]` references embedded in the report file to render inside the artifact Markdown viewer.
- If `present_artifact` is not visible in the current deployment, fall back to the v0.8 contract (full Markdown report + separate citation JSON returned in the response body). See the SKILL "Output firewall" section.

## Deliverables

Two files are produced each run:

1. **Report file** — `/workspace/output/<slug>-report.md`
   - `<slug>` is a short ASCII descriptive name (lowercase letters, digits, hyphens; no spaces, no slashes, no dots), e.g. `harmoni6`, `nsclc-3g-tki-comparison`, `ad-easi75-group`.
   - Content = the routed report template (`templates/unified-evidence-report.md` for one trial, `templates/cross-trial-report.md` or `templates/mixed-comparison-report.md` for different/mixed trials), fully filled in: starts with the title (no intro), contains inline `{{ref_n}}` markers and `::visualization[...]` references to charts under `/workspace/visualizations/`.
   - This file is the single presented card.

2. **Citation file** — `/workspace/output/<slug>-citations.json`
   - Raw strict JSON, one key per selected source in input order: `{"ref_1":{"title":…,"link":…,"paper_release_time_str":…},…}`.
   - Same schema as the v0.8 separate citation JSON (see `references/citation-and-ref.md`); fields copied byte-for-byte from the attached source files.
   - Not presented as a card: it is the machine-readable source listing for downstream marker rendering. It is still a visible workspace artifact (any file under `/workspace/output/` is listed by the artifacts API and the artifact panel).

## Delivery sequence (terminal action)

1. Write chart product files to `/workspace/visualizations/` first and run `templates/charts/validate-chart.py` until PASS (per `references/chart-templates.md`).
2. Write the complete report Markdown to `/workspace/output/<slug>-report.md`.
3. Write the citation JSON to `/workspace/output/<slug>-citations.json` (raw JSON, no code fences, no commentary).
4. Verify before presenting:
   - the report file is readable and every template placeholder is replaced;
   - marker/key parity holds (every `{{ref_n}}` in the report has a matching JSON key and every key is used — see `references/citation-and-ref.md`);
   - every chart product referenced in the report exists under `/workspace/visualizations/` and passed `validate-chart.py`;
   - citation fields exactly match the supplied metadata.
5. Call `present_artifact('/workspace/output/<slug>-report.md')` as the **final tool call**. Once it succeeds, end the response immediately: do not call any further tool and do not append report text.

## Chat body rule (empty body — 方案 B)

- The response body must be **empty**, or at most one short sentence stating the file's purpose (e.g. 「完整报告已生成，见下方文件卡片」).
- Never place report content, intro text, summaries, conclusions, or citation listings in the body.
- Never call any tool after `present_artifact`.

## Interoperability and limits

- Present only the report file. Do not separately present the visualizations embedded via `::visualization[...]` unless one is itself an independent requested deliverable.
- `{{ref_n}}` markers stay inside the report file (unchanged contract). Downstream consumers render them as numeric superscript links using the citation file.
- Re-presenting the same path in a later turn is allowed and is the signal that clients fetch the current version again.
- Keep the report within the text-preview limit (1 MiB / 20 000 lines) when possible; larger reports remain downloadable.
