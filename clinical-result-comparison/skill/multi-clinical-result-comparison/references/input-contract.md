# Backend Input Contract

## Purpose

Each selected clinical result is delivered to the Agent as **one attached file** (`.md`), not as inline JSON in a message. The frontend sends all selected files as attachments in the user turn; the backend resolves the four consumer fields from the POC Elasticsearch environment before writing the files. The Agent reads the attached files from the workspace uploads directory and assigns `{{ref_n}}` markers in file order.

Rationale: a user may select many results (for example 20–50). Inline JSON in a single message can exceed the context budget; per-source files keep each result addressable, make the context bounded by what the Agent actually reads, and keep the citation mapping stable (`source-003.md` → `{{ref_3}}`).

## Elasticsearch lookup

- Use the POC project configuration loader at `/home/xupeipeioo1/apps/POC/src/config.js` for `ES_HOST`, `ES_USERNAME`/`ES_PASSWORD`, or `ES_API_KEY`.
- Query the `np_clinical` index. An optional `NP_CLINICAL_INDEX` environment variable may override the default for a deployment, but the default is `np_clinical`.
- Request only the source fields required for this Agent: `base.title`, `base.full_article_link`, and `source_full_text`. For the current index data, also request `base.paper_title` as a title compatibility fallback and `base.paper_release_time_str` for the citation timestamp.
- Resolve either the Elasticsearch document ID or the selected record's composite key by extracting the portion after `::` for an ID query and retaining the original selection order only in backend memory.
- Exclude deleted records according to the backend's existing selection policy. Do not pass technical record IDs into the Agent.

The current `np_clinical` index was checked read-only against four HARMONi-6 records. `base.full_article_link` and `source_full_text` are `{meta, text}` objects. `base.title` is mapped but empty for these records; `base.paper_title.text` contains the source title. This fallback is a data-shape compatibility rule, not a generated title.

## Per-source attachment file

Normalize each selected record to this consumer-facing shape:

```json
{
  "source_title": "value from base.title.text, otherwise base.paper_title.text",
  "source_url": "value from base.full_article_link.text",
  "source_paper_release_time_str": "value from base.paper_release_time_str.text",
  "source_full_text": "value from source_full_text.text"
}
```

Write one `.md` file per selected result, named by input order. The file has exactly this layout (metadata between the `#` heading and the `## source_full_text` heading; the entire body after the heading is the full text):

```markdown
# 临床结果来源 {n}

source_title: {title}
source_url: {url}
source_paper_release_time_str: {time}

## source_full_text

{source_full_text}
```

Filename convention: `source-{n}.md`, where `{n}` is the 1-based input-order index left-padded to three digits (`source-001.md`, `source-002.md`, …). The file order defines the `{{ref_n}}` marker scope for the whole response. Do not include `result_id`, `doc_id`, Elasticsearch `_id`, index names, storage paths, structured clinical fields, or retrieval diagnostics in the file or filename.

`source_url` must be copied byte-for-byte from `base.full_article_link.text`. The backend may reject a non-empty URL that is not absolute `http`/`https`, but it must never repair or guess one. A missing title, URL, or release time is represented by an empty value after its colon and remains visible as missing citation metadata; the Agent must not invent a replacement.

## Attachment delivery and limits

- The frontend sends the files as `file` parts in the user message (`.md` with `text/markdown` media type). Base64-encode each file as `data:text/markdown;base64,...`. The backend accepts only the documented attachment formats and media types.
- Attachment limits (Tool Smith): up to **10 files per message**, up to **100 files per thread**, up to **20 MiB per file**, extracted text ≤ 50 MiB per request, thread raw files ≤ 50 MiB. If the user selects more than 10 results at once, split the delivery into multiple user turns or threads; the Agent simply processes whatever attached files it receives and must not assume a fixed count.
- Uploaded originals live under `/workspace/uploads/` and the Agent reads them from there. The Agent must read every attached file and must not silently skip an accepted source; an unreadable or empty source is recorded in the source inventory as a limitation, not dropped.
- Do not append inline JSON summaries or re-send full text in the message body. The files are the source of record; the text part of the message only states the task.

## Agent reading protocol

1. List the attached source files in the workspace uploads directory.
2. Order them by filename (`source-001.md`, `source-002.md`, …); that is the input order and the `{{ref_n}}` assignment order. Filename order is a presentation label, not clinical chronology.
3. For each file, read the `source_title`, `source_url`, and `source_paper_release_time_str` values from the metadata lines and the full text from the body after `## source_full_text`.
4. Build the internal worksheet exactly as described in `references/input-and-extraction.md`, using the same rules that previously applied to inline source objects.

## Large-batch delegation via subagents (OPTIONAL, pending verification)

> ⚠️ Status: **not yet validated in a real Tool Smith deployment.** Keep this as an opt-in strategy; the default path remains "Agent reads every attached file directly" per the protocol above.

When the deployment exposes the `task` tool (backend `SubAgentCapability` registered and `capabilities_config.subagents` enabled) and the number of attached files is large (recommendation: ≥ 20), the Agent MAY delegate extraction to subagents to keep the main-thread context bounded. This is a performance strategy, **not a change to the evidence boundary**: only `source_full_text` read from the files is evidence, and every extracted value must still carry its source file number.

- **Chunking**: split the attached files by filename order into chunks of at most 10 files each (e.g. 50 files → 5 chunks: `source-001..010`, …, `source-041..050`). Chunk boundaries must never reorder filenames.
- **One `task` call per chunk**: `subagent_type: "general-purpose"`, with a fully self-contained `description` stating exactly which files to read (e.g. `source-001.md` … `source-010.md` in `/workspace/uploads/`), the exact per-trial fields to extract (same as the evidence worksheet in `references/input-and-extraction.md`), and the exact compact output format including the source file number on every extracted value.
- **Output discipline**: the subagent returns only a compact structured summary (short trial name, arm/label, endpoint values, p-values/CIs, source file number). Keep the returned text small (a few hundred characters per trial) so 5–10 summaries do not re-bloat the main thread.
- **Citation correctness**: `{{ref_n}}` assignment stays global by filename order (`source-003.md` → `{{ref_3}}`) regardless of which chunk processed it. Subagents must echo the source file number; the main Agent maps those to ref markers and deduplicates.
- **Constraints**: subagents are stateless (single `description`, no follow-ups — put everything needed in it); recursive depth is limited (do not nest delegation deeper than one level); multiple `task` calls in one message are allowed but concurrency is not guaranteed — treat serial execution as acceptable.
- **Fallback**: if the `task` tool is not visible/available, ignore this section and read every attached file directly (default protocol). Never skip a source because delegation is unavailable.

**Verification checklist before enabling as default** (see pending questions with the Tool Smith developer):
1. `capabilities_config.subagents` is enabled on the deployment and `task` is visible to the Agent.
2. 20–50 attachments actually land in `/workspace/uploads/` across split messages and are all readable in one run.
3. Concurrent `task` calls are either truly concurrent or acceptably fast serially.
4. Measured token cost: 5–10 compact summaries + aggregation stay well under the run budget.

## Citation rendering

The Agent emits machine-readable `{{ref_n}}` tokens in the Markdown report. The citation metadata is a separate JSON artifact and must not be appended to the report or passed through a generic Markdown autolinker. The frontend receives the report and citation JSON separately, validates marker/key parity, then renders only the report body.

```html
<sup class="source-citation"><a href="SUPPLIED_LINK" title="SUPPLIED_TITLE" target="_blank" rel="noopener noreferrer">n</a></sup>
```

Render only validated `http`/`https` links. Escape the title and URL for HTML attributes, prevent arbitrary HTML interpolation, and leave the marker as plain text or an unavailable citation state when the link is empty. Only the numeric superscript is clickable; never wrap the surrounding sentence, paragraph, table cell, or punctuation in the citation anchor. Do not expose the citation JSON in the visible report body.

## Reproducible local check

From the Agent project, pull a batch by condition and write one attachment file per source:

```bash
node --env-file=/home/xupeipeioo1/apps/POC/.env \
  evals/fetch-np-clinical-attachments.mjs \
  evals/iteration-16/np-clinical-nsclc-50 50
```

The command queries the default condition (non-small-cell lung cancer, phase 3, positive evaluation), writes `source-*.md` files plus a `manifest.json` (input order → normalized object) to the output directory, and never prints credentials. The manifest is for backend logging/verification only and must not be shown to the Agent or included in the report. Production request orchestration remains owned by the backend; this adapter is a validation/reference implementation.
