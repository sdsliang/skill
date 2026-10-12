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
- **Always pass `overwrite=True` on every `write_file` call, including the first write of a brand-new path** (it is a no-op when the path does not exist yet, while `overwrite` defaults to `False`). Do not stop to work out whether a path is new: every path this run already created — the report, `work/ledger.json`, `work/draft.md`, digest files, chart JSON, and especially the helper scripts you author yourself (`/workspace/scripts/*.py`) — makes a call that omits the flag a refused call, and one refused call counts as a tool error. Write each file once; write each helper script once and re-run it rather than rewriting it. If a revision really is needed, re-issue the whole file with `overwrite=True`. **`edit_file` is scoped to the report body**: never patch a file this run generated (`/workspace/scripts/*.py`, the ledger JSON, digests, anything under `work/`) — re-issue the whole file instead — and use `edit_file` on the report only with a short `old_string` you have just seen in a `read_file` result, because a stale `old_string` is refused and a refused call fails the whole run.
- The chart kind is carried by the file name (`endpoint-bar-*` vs `endpoint-line-*`) and must match the JSON `type` field (`"type": "bar"` / `"type": "line"`). The renderer dispatches on `type`, while the file name is the stable human/backend index. A lone quantitative chart therefore always sits at `/workspace/visualizations/endpoint-bar-1.json` or `/workspace/visualizations/endpoint-line-1.json`; cross-trial/mixed inputs number each kind independently in report order.
- Chart paths need no backend derivation either, because the report carries each path verbatim inside its `::visualization[...]` reference. Keep every path ASCII, lowercase, hyphen-separated, and directly under those two directories (no subdirectories, no `..`, no backslashes).

- **Create each parent directory in the same command as the first write into it (empty-dir fallback).** Run `mkdir -p /workspace/output /workspace/visualizations` **together with** the first write into those paths, not in an earlier step: empty directories do not reliably survive between `execute` calls, so a later write can fail with `FileNotFoundError: /workspace/output/citations.json` even though an earlier `mkdir` appeared to succeed. Never assume an empty directory created in a previous step still exists; if a write reports the directory missing, re-run `mkdir -p` and the write in one command and continue. This covers **shell redirection targets** as well: `python gen.py > /workspace/visualizations/endpoint-bar-1.json` must be issued together with `mkdir -p /workspace/visualizations`, because the shell resolves the redirection target before the script runs.

## Deliverables

Two files are produced each run:

1. **Report file** — `/workspace/output/report.md` (fixed path, per the naming contract)
   - The file name is not part of the content decision: do not encode the trial, indication, endpoint, date, or selected-set size into it.
   - **The body is written once, straight to this path** (`references/toolbox.md`): author it with `[[fact:…]]` / `[[result:…]]` tokens standing in for the values the ledger owns, then render it **in place** with a single `render-facts.py` pass (`--ledger work/ledger.json --draft /workspace/output/report.md --out /workspace/output/report.md --audit work/audit.json` — the same path for `--draft` and `--out` is intended and safe). **There is no draft stage**: no `work/draft.md`, no scratch render, no second copy, no re-assembly from N chunk writes. Later wording fixes go through `python3 /workspace/skills/multi-clinical-result-comparison/scripts/patch.py` (asserted, atomic) — not a whole-file rewrite, and re-render only if a token moved.
   - Content = the routed report template (`templates/unified-evidence-report.md` for one trial, `templates/cross-trial-report.md` or `templates/mixed-comparison-report.md` for different/mixed trials), fully filled in: starts with the title (no intro), contains inline `{{ref_n}}` markers and `::visualization[...]` references to charts under `/workspace/visualizations/`.
   - This file is the single presented card.

2. **Citation file** — `/workspace/output/citations.json` (fixed path)
   - The fixed machine-readable sibling of the report; the backend hard-codes both paths, so never rename, relocate, or suffix either one.
   - Raw strict JSON, one key per **retrieved** source in selection (esid) order over the records that returned: `{"ref_1":{"title":…,"link":…,"paper_release_time_str":…},…}`. An esid that returned no record gets no key (never write an entry with an empty `title`; see `references/input-contract.md`, *Unretrievable selected items*). **Build it with `python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_citations.py --report /workspace/output/report.md`** (`references/toolbox.md`): it copies `title`/`link` byte-for-byte out of `work/refs.json` (never retype them — the script is how the byte-for-byte rule is actually met) and keeps the keys equal to the refs the report cites, so parity holds by construction; its `--full-text ref_n=<URL>` is the C1/C2 substitution flag for a record analysed from a retrieved PMC full text.
   - Same schema as the v0.8 separate citation JSON (see `references/citation-and-ref.md`); `title` is copied byte-for-byte from `paper_title`; `link` follows `references/input-contract.md`, *Citation link follows the analysis depth* (C1/C2 only for retrieved, archived PMC full text used in analysis; otherwise byte-for-byte `full_article_link`), and `paper_release_time_str` is the **date part only** (`YYYY-MM-DD`) of `paper_release_time` — that field returns a datetime string (`YYYY-MM-DD HH:MM:SS`), so drop the time component, never reformat further, and leave the value empty when the record has none.
   - Not presented as a card: it is the machine-readable source listing for downstream marker rendering. It is still a visible workspace artifact (any file under `/workspace/output/` is listed by the artifacts API and the artifact panel).

## Delivery sequence (terminal action)

1. Write chart product files to `/workspace/visualizations/` under the fixed names from the naming contract first, via `python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_chart.py` (each product is written and validated by the script — envelope `{ id, iframe_template, option }` taken from the live chart skill, never hand-copied, never hardcoded; per `references/chart-templates.md`).
2. Write the report body **once** to `/workspace/output/report.md` and render it in place with one `render-facts.py` pass (`--draft` == `--out`); no `work/draft.md` stage.
3. Build the citation JSON at `/workspace/output/citations.json` with `python3 /workspace/skills/multi-clinical-result-comparison/scripts/make_citations.py` (raw JSON, no code fences, no commentary).
4. Verify before presenting — run `python3 /workspace/skills/multi-clinical-result-comparison/scripts/check_report.py -v` and fix every FAIL (it is the mechanical subset of the list below: marker/citation parity both ways, citation entry shape, chart envelope keys/type/path, appendix presence, internal leaks); then:
   - The report file is readable and every template placeholder is replaced;
   - the deliverable paths are exactly `/workspace/output/report.md` and `/workspace/output/citations.json` (no slug, date, index, or other suffix) and both files exist and are readable;
   - every chart product sits at its fixed name (`evidence-timeline.json`, `endpoint-bar-<n>.json`, `endpoint-line-<n>.json`) and each file's JSON `type` matches its file name;
   - marker/key parity holds (every `{{ref_n}}` in the report has a matching JSON key and every key is used — see `references/citation-and-ref.md`);
   - every chart product referenced in the report exists under `/workspace/visualizations/` and passed the chart skill CLI validation;
   - citation fields follow `references/input-contract.md`: `title` byte-for-byte from `paper_title`, `link` byte-for-byte from `full_article_link` or the required C1/C2 substitution backed by the retrieved, archived full text, and `paper_release_time_str` equal to the `YYYY-MM-DD` date part of `paper_release_time` (no `HH:MM:SS`, no reformatting).
5. Call `present_artifact('/workspace/output/report.md')` as the **final tool call** (after `check_report.py` exits 0 — warnings are printed but never block). Once it succeeds, end the response immediately: do not call any further tool and do not append report text.

## Chat body rule (empty body — 方案 B)

- The response body must be **empty**, or at most one short sentence stating the file's purpose (e.g. 「完整报告已生成，见下方文件卡片」).
- Never place report content, intro text, summaries, conclusions, or citation listings in the body.
- Never call any tool after `present_artifact`.

## Interoperability and limits

- Present only the report file. Do not separately present the visualizations embedded via `::visualization[...]` unless one is itself an independent requested deliverable.
- `{{ref_n}}` markers stay inside the report file (unchanged contract). Downstream consumers render them as numeric superscript links using the citation file.
- Re-presenting the same path in a later turn is allowed and is the signal that clients fetch the current version again.
- Keep the report within the text-preview limit (1 MiB / 20 000 lines) when possible; larger reports remain downloadable.
