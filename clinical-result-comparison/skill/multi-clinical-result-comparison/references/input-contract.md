# Backend Input Contract

## Purpose

The backend resolves selected records from the POC Elasticsearch environment before invoking the Agent. The frontend does not append or construct article links.

## Elasticsearch lookup

- Use the POC project configuration loader at `/home/xupeipeioo1/apps/POC/src/config.js` for `ES_HOST`, `ES_USERNAME`/`ES_PASSWORD`, or `ES_API_KEY`.
- Query the `np_clinical` index. An optional `NP_CLINICAL_INDEX` environment variable may override the default for a deployment, but the default is `np_clinical`.
- Request only the source fields required for this Agent: `base.title`, `base.full_article_link`, and `source_full_text`. For the current index data, also request `base.paper_title` as a title compatibility fallback.
- Resolve either the Elasticsearch document ID or the selected record's composite key by extracting the portion after `::` for an ID query and retaining the original selection order only in backend memory.
- Exclude deleted records according to the backend's existing selection policy. Do not pass technical record IDs into the Agent.

The current `np_clinical` index was checked read-only against four HARMONi-6 records. `base.full_article_link` and `source_full_text` are `{meta, text}` objects. `base.title` is mapped but empty for these records; `base.paper_title.text` contains the source title. This fallback is a data-shape compatibility rule, not a generated title.

## Agent payload

Normalize each selected record to exactly this consumer-facing shape:

```json
{
  "source_title": "value from base.title.text, otherwise base.paper_title.text",
  "source_url": "value from base.full_article_link.text",
  "source_paper_release_time_str": "value from base.paper_release_time_str.text",
  "source_full_text": "value from source_full_text.text"
}
```

Do not include `result_id`, `doc_id`, Elasticsearch `_id`, index names, storage paths, structured clinical fields, or retrieval diagnostics. Keep the backend record-to-source mapping outside the model request for operational logging only.

`source_url` must be copied byte-for-byte from `base.full_article_link.text`. The backend may reject a non-empty URL that is not absolute `http`/`https`, but it must never repair or guess one. A missing title or link is represented by an empty string and remains visible as missing citation metadata; the Agent must not invent a replacement.

## Citation rendering

The Agent emits machine-readable `{{ref_n}}` tokens in the Markdown report. The citation metadata is a separate JSON artifact and must not be appended to the report or passed through a generic Markdown autolinker. The frontend receives the report and citation JSON separately, validates marker/key parity, then renders only the report body.

```html
<sup class="source-citation"><a href="SUPPLIED_LINK" title="SUPPLIED_TITLE" target="_blank" rel="noopener noreferrer">n</a></sup>
```

Render only validated `http`/`https` links. Escape the title and URL for HTML attributes, prevent arbitrary HTML interpolation, and leave the marker as plain text or an unavailable citation state when the link is empty. Only the numeric superscript is clickable; never wrap the surrounding sentence, paragraph, table cell, or punctuation in the citation anchor. Do not expose the citation JSON in the visible report body.

## Reproducible local check

From the Agent project, provide selected Elasticsearch IDs to the adapter and load the POC environment explicitly:

```bash
node --env-file=/home/xupeipeioo1/apps/POC/.env evals/fetch-np-clinical-sources.mjs 24_1_41125109
```

The command writes normalized JSON to stdout and never prints credentials. The adapter is a validation/reference implementation; production request orchestration remains owned by the backend.
