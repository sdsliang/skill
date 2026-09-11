# File Deliverable Contract (v0.9)

## Purpose

The finished consumer-facing report is delivered as a **workspace file** presented through the Tool Smith `present_artifact` capability, not as streamed chat text. This lets the backend serve the file directly (no parsing of model output), prevents uncontrolled intro text or trailing tool calls, and gives the report a stable, downloadable, shareable form.

## Deployment requirements

- The project must have the **`artifact_presentation`** capability enabled (per-project switch, default OFF) for `present_artifact` to be visible to the root agent.
- The **`visualization`** capability must also be enabled for `::visualization[...]` references embedded in the report file to render inside the artifact Markdown viewer.
- If `present_artifact` is not visible in the current deployment, fall back to the v0.8 contract (full Markdown report + separate citation JSON returned in the response body). See the SKILL "Output firewall" section.

## Naming contract (hard rule — paths are fixed so the backend can hard-code them)

The deliverable paths are **constant across runs**. Never derive them from the trial name, the selected set, the comparison topic, or any runtime value, and never append a slug, date, index, or other suffix to the two output files.

| Deliverable | Fixed path |
| --- | --- |
| Report | `/workspace/output/report.md` |
| Citation JSON | `/workspace/output/citations.json` |
| Evidence-chain timeline chart (only when generated) | `/workspace/visualizations/evidence-timeline.json` |
| Quantitative **bar** chart *n* (n = that kind's order in the report, from 1) | `/workspace/visualizations/endpoint-bar-<n>.json` |
| Quantitative **line** chart *n* (n = that kind's order in the report, from 1) | `/workspace/visualizations/endpoint-line-<n>.json` |

- The backend **hard-codes** `/workspace/output/report.md` and `/workspace/output/citations.json` and does **not** read the path back from the `present_artifact` result. If either path drifts, the citation file is orphaned and downstream marker rendering silently fails.
- Reruns in the same workspace **overwrite** these files in place. That is intended: one current report per workspace, consistent with the platform rule that a presented path means "the current version of this path", not an immutable version link. Never work around it by inventing suffixed names.
- The chart kind is carried by the file name (`endpoint-bar-*` vs `endpoint-line-*`) and must match the JSON `type` field (`"type": "bar"` / `"type": "line"`). The renderer dispatches on `type`, while the file name is the stable human/backend index. A lone quantitative chart therefore always sits at `/workspace/visualizations/endpoint-bar-1.json` or `/workspace/visualizations/endpoint-line-1.json`; cross-trial/mixed inputs number each kind independently in report order.
- Chart paths need no backend derivation either, because the report carries each path verbatim inside its `::visualization[...]` reference. Keep every path ASCII, lowercase, hyphen-separated, and directly under those two directories (no subdirectories, no `..`, no backslashes).

- **Create each parent directory in the same command as the first write into it (empty-dir fallback).** Run `mkdir -p /workspace/output /workspace/visualizations` **together with** the first write into those paths, not in an earlier step: empty directories do not reliably survive between `execute` calls, so a later write can fail with `FileNotFoundError: /workspace/output/citations.json` even though an earlier `mkdir` appeared to succeed. Never assume an empty directory created in a previous step still exists; if a write reports the directory missing, re-run `mkdir -p` and the write in one command and continue.

## Deliverables

Two files are produced each run:

1. **Report file** — `/workspace/output/report.md` (fixed path, per the naming contract)
   - The file name is not part of the content decision: do not encode the trial, indication, endpoint, date, or selected-set size into it.
   - Content = the routed report template (`templates/unified-evidence-report.md` for one trial, `templates/cross-trial-report.md` or `templates/mixed-comparison-report.md` for different/mixed trials), fully filled in: starts with the title (no intro), contains inline `{{ref_n}}` markers and `::visualization[...]` references to charts under `/workspace/visualizations/`.
   - This file is the single presented card.

2. **Citation file** — `/workspace/output/citations.json` (fixed path)
   - The fixed machine-readable sibling of the report; the backend hard-codes both paths, so never rename, relocate, or suffix either one.
   - Raw strict JSON, one key per selected source in input (esid) order: `{"ref_1":{"title":…,"link":…,"paper_release_time_str":…},…}`.
   - Same schema as the v0.8 separate citation JSON (see `references/citation-and-ref.md`); the three values are copied byte-for-byte from the pulled record's `paper_title` / `full_article_link` / `paper_release_time` fields.
   - Not presented as a card: it is the machine-readable source listing for downstream marker rendering. It is still a visible workspace artifact (any file under `/workspace/output/` is listed by the artifacts API and the artifact panel).

## Delivery sequence (terminal action)

1. Write chart product files to `/workspace/visualizations/` under the fixed names from the naming contract first, and run the chart skill CLI (`node /workspace/skills/chart-visualization-json/scripts/validate-cli.js <成品>`) until PASS (per `references/chart-templates.md`). Each product must be the chart skill **envelope** (`{ id, iframe_template, option }`), not a bare `option` object: copy the chart skill's own `templates/{bar,line,timeline}.json` and replace only its `option` body. `iframe_template` is refreshed on every chart publish, so read it from that template (or its `config.js`) at run time — never hardcode it.
2. Write the complete report Markdown to `/workspace/output/report.md`.
3. Write the citation JSON to `/workspace/output/citations.json` (raw JSON, no code fences, no commentary).
4. Verify before presenting:
   - The report file is readable and every template placeholder is replaced;
   - the deliverable paths are exactly `/workspace/output/report.md` and `/workspace/output/citations.json` (no slug, date, index, or other suffix) and both files exist and are readable;
   - every chart product sits at its fixed name (`evidence-timeline.json`, `endpoint-bar-<n>.json`, `endpoint-line-<n>.json`) and each file's JSON `type` matches its file name;
   - marker/key parity holds (every `{{ref_n}}` in the report has a matching JSON key and every key is used — see `references/citation-and-ref.md`);
   - every chart product referenced in the report exists under `/workspace/visualizations/` and passed the chart skill CLI validation;
   - citation fields exactly match the pulled records' `paper_title` / `full_article_link` / `paper_release_time`.
5. Call `present_artifact('/workspace/output/report.md')` as the **final tool call**. Once it succeeds, end the response immediately: do not call any further tool and do not append report text.

## Chat body rule (empty body — 方案 B)

- The response body must be **empty**, or at most one short sentence stating the file's purpose (e.g. 「完整报告已生成，见下方文件卡片」).
- Never place report content, intro text, summaries, conclusions, or citation listings in the body.
- Never call any tool after `present_artifact`.

## Interoperability and limits

- Present only the report file. Do not separately present the visualizations embedded via `::visualization[...]` unless one is itself an independent requested deliverable.
- `{{ref_n}}` markers stay inside the report file (unchanged contract). Downstream consumers render them as numeric superscript links using the citation file.
- Re-presenting the same path in a later turn is allowed and is the signal that clients fetch the current version again.
- Keep the report within the text-preview limit (1 MiB / 20 000 lines) when possible; larger reports remain downloadable.
