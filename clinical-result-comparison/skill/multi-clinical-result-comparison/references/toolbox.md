# Toolbox — the six packaged scripts (use these, do not write your own)

Every mechanical step of this Skill already has a script, shipped inside this bundle under
`scripts/` (next to `render-facts.py`). **Run them; do not re-implement them.** Writing your own
`build_ledger.py` / `fix_draft.py` / `digest.py` / `clean_draft.py` helper is the single largest
waste in this pipeline (measured: 25–55 % of one run's output tokens, and the source of every
"I could not find the target string" re-prompt). If a step below does not do what you need,
extend the command with its documented flags, or report the gap — do not write a replacement.

At run time this bundle is mounted at `/workspace/skills/multi-clinical-result-comparison/`, so
invoke each script by its full path — `python3 /workspace/skills/multi-clinical-result-comparison/scripts/<name>.py …`. A bare `scripts/…`
does **not** resolve from cwd `/workspace`. Below, `scripts/<name>.py` is shorthand for that
directory. Defaults are the contract paths; pass an explicit flag only to deviate.

| Step | Script | Writes |
| --- | --- | --- |
| Pull → readable sources + ref inventory | `scripts/prep_sources.py` | `work/sources/ref_<n>.txt`, `work/refs.json` |
| Facts → strict ledger (+ the only validation) | `scripts/build_ledger.py` | `work/ledger.json` |
| Body + appendix + `{{ref_n}}` | `scripts/render-facts.py` | `/workspace/output/report.md` (in place) |
| Any small edit to an existing file | `scripts/patch.py` | the file, in place |
| Chart product | `scripts/make_chart.py` | `/workspace/visualizations/<fixed name>.json` |
| Citation JSON | `scripts/make_citations.py` | `/workspace/output/citations.json` |
| Final mechanical check | `scripts/check_report.py` | nothing (exit code only) |

Run them one after another in a **single `execute` call** where the steps are independent
(e.g. `mkdir -p`, then `prep_sources`, then `build_ledger` in one shell line) instead of one call
per script.

## 1. `prep_sources.py` — the pulled records into files you can read

```
python3 scripts/prep_sources.py --esids <esid_1,esid_2,…>            # selection order
python3 scripts/prep_sources.py --esids-file work/selected.txt      # one esid per line, # comments
python3 scripts/prep_sources.py --esids … --full --quiet
```

* `--result PATH` — the raw `tool_results/**/*.jsonl` pull; omitted, the newest pull with records
  under `--tool-results` (default `/workspace/tool_results`) is used.
* `--sources-dir` (default `work/sources`), `--refs` (default `work/refs.json`),
  `--body-chars` (digest body cap, default 4000), `--full` (whole bodies in the digest),
  `--quiet` (files only).
* refs are numbered in **selection order**, only over esids that came back; a missing esid is
  reported and consumes **no** number (it is not a row in the report, not a marker, not a
  citation entry). A duplicate esid keeps its first ref and is reported on stderr.
* Each `work/sources/ref_<n>.txt` holds the record's own text (title/link/release metadata, the
  abstract or summary body, arms, study results) — this is the file `build_ledger` verifies
  `quote` against, and it is the surface a fact's evidence depth is measured on.
* `work/refs.json` carries `title`, `link`, `paper_release_time_str` (date part only) plus the
  clinical fields used for identity. `make_citations.py` copies `title`/`link` byte-for-byte.
* Exit `0` all found · `3` at least one selected esid returned no record (files still written for
  the rest) · `2` usage/IO.

## 2. `build_ledger.py` — validate the fact ledger

```
python3 scripts/build_ledger.py --stats          # fact counts by ref and kind
python3 scripts/build_ledger.py --check           # validate only, write nothing
python3 scripts/build_ledger.py                   # write work/ledger.json
```

* Input `--facts` (default `work/facts.json`), output `--out` (default `work/ledger.json`),
  `--refs` for trial/`source_file` defaults.
* You author `facts.json` (the clinical judgment); the script does every mechanical check and
  writes the strict shape `render-facts.py` accepts: `{"records":[…],"facts":[…]}`. Each record
  = `ref` + `identity` + `conclusion` (optionally `trial`, `title`, `design`, `arms`, `coverage`);
  each fact = the 15 fields `id, ref, study, version, endpoint, arm, population, timepoint,
  assessment, kind, value, unit, statistics, source_file, quote` — absent
  `version`/`population`/`timepoint`/`assessment` are filled with `未报告`, `statistics` with `""`.
  `kind` ∈ `试验设计｜试验结论｜有效性｜安全性｜PK/PD｜PRO｜其他` (a `·家族` suffix is allowed).
* Checks that fail the whole compile (exit 3, **nothing written**, existing ledger untouched) and
  are printed together: `quote` is not an exact substring of that ref's source file, `value` is
  absent from `quote`, `kind` outside the vocabulary, duplicate `id`, unknown `ref`, more than one
  `study` per ref. A failing compile never leaves a half-written ledger.
* Exit `0` written (or clean under `--check`) · `3` findings · `2` usage/IO.

## 3. `render-facts.py` — body + appendix, in one write

```
python3 scripts/render-facts.py --ledger work/ledger.json --draft /workspace/output/report.md \
        --out /workspace/output/report.md --audit work/audit.json
```

`--draft` **and** `--out` may be the same path: the script reads the whole draft, resolves every
`[[fact:id]]` / `[[result:id]]` token, appends the evidence-alignment appendix and replaces the
file atomically. So the body is written **once**, in the canonical form, and rendered in place —
there is no separate `work/draft.md` stage and no second copy. Exit `3` on a schema/validation
failure (unknown token id, missing field) with nothing written.

## 4. `patch.py` — asserted, atomic, whole-file find/replace

```
python3 scripts/patch.py <file> --find '<text>' --replace '<text>' [--count N]
python3 scripts/patch.py <file> --find '<text>' --count 0        # assert absent, change nothing
python3 scripts/patch.py <file> --find '<anchor>' --replace $'\n<new paragraph>' --insert-after --unescape
```

* Default `--count 1`: the number of matches **must** equal it, otherwise exit 3 and the file is
  left untouched (the match context is printed so you can see what differed). `--count 0` asserts
  the text is absent.
* `--replace ''` / `--delete` removes; `--find-file` / `--replace-file` read the payload from a
  file (use them for multi-line CJK text instead of shell-quoting); `--unescape` turns `\n`/`\t`
  into real characters; `--dry-run` reports without writing.
* **A `--find` value that starts with `-` needs the equals form**: `--find=-5.3` (argparse reads
  `--find -5.3` as a flag). Same for `--replace`.
* Use this instead of authoring a one-off fix script, and instead of `edit_file` on anything that
  is not the report body.
* Exit `0` applied · `3` assertion failed (nothing written) · `2` usage/IO.

## 5. `make_chart.py` — one chart product from a content-only spec

```
python3 scripts/make_chart.py work/charts/endpoint-bar-1.json
```

* You write **only the content**: `type` (`bar`|`line`|`timeline`), `file` (the fixed product
  name), `title`, `subTitle`, `dataSource`, `describe`, `axisXTitle`/`axisYTitle` (bar/line),
  `data[]`. The script pulls the skeleton from this Skill's `templates/charts/` and the envelope
  (`id` + `iframe_template`) from the mounted `chart-visualization-json` skill, then validates
  with the upstream CLI. Never hand-write the envelope and never hardcode `iframe_template`.
* `data` rows: bar/line = `{label, value, description}` (line also needs `group`); timeline =
  `{label, content, description, time}` where `time` is the anchor (`YYYY-MM`). `description`
  carries the `{{ref_n}}` markers; the figure is the skeleton, the numbers live in the tables.
* Fixed product names: `endpoint-bar-<n>.json`, `endpoint-line-<n>.json` (n = order of that type
  in the report), `evidence-timeline.json`. A `file`/`type` mismatch or a slug name exits 2.
* `--sort auto|none|value-desc|value-asc|time-asc` (defaults: bar `value-desc`, line `none`,
  timeline `time-asc`), `--strict` (warnings become failures), `--dry-run`, `--json`.
* Exit `0` written and validated · `3` structural finding, nothing written (missing label/
  description, empty or non-numeric `data`, a timeline event without `time`, a line row without
  `group`) · `4` written but the validator is unavailable — say so, never call it validated · `2`
  usage/IO.
* Warnings only (on stderr): label > 18 / content > 16 characters, and a digit outside the `time`
  anchor in a timeline row (registry ids such as `NCT02729025` are exempt). `--strict` fails them.

## 6. `make_citations.py` — the citation JSON

```
python3 scripts/make_citations.py --report /workspace/output/report.md
python3 scripts/make_citations.py --report … --full-text ref_2=https://pmc.ncbi.nlm.nih.gov/articles/PMC…
```

* Built from `work/refs.json`; each entry is exactly `{title, link, paper_release_time_str}` with
  `title`/`link` copied byte-for-byte from the pulled record and the release time reduced to
  `YYYY-MM-DD`.
* With `--report`, only refs the report actually cites are written (unused keys are dropped with
  a NOTE — this is what keeps citations ⇄ markers in parity); a report marker with no refs entry,
  an entry with an empty title, or a record that never came back exits 3 with nothing written.
  `--keep-unused` keeps everything (only for debugging), `--check` validates without writing,
  `--print` echoes the body.
* `--full-text ref_n=URL` is the C1/C2 substitution for a record whose facts rest on a retrieved
  PMC full text (repeatable, `http(s)://` only). Exit `0` · `3` parity/format finding · `2` IO.

## 7. `check_report.py` — the mechanical pre-delivery pass

```
python3 scripts/check_report.py -v            # then fix what it printed and re-run
```

Checks the report text (unresolved `[[fact:…]]` tokens, `{{…}}` braces that are not `ref_n`
markers, `entity:` syntax, the appendix title **and** that it has data rows), marker ⇄ citation
parity in both directions, citation entry shape (empty title, extra fields, a fenced code block),
chart products (envelope keys exactly `{id, iframe_template, option}`, non-empty data, type vs
file name, and that every `::visualization` target exists under the fixed prefix), plus internal
leaks in the delivered text (`source_file`, `tool_results`, `esid`, `/workspace/work/`, a
`ledger|facts.json` path, a Mermaid block). Warnings only: run-logistics wording, a chart product
never referenced by the report, a table cell citing the same ref twice, and chart text sharing an
8-character run with a table cell (registry ids and citation-title text are exempt).
Exit `0` all green · `3` at least one FAIL · `4` warnings only · `2` usage/IO. Run it **before**
`present_artifact`; the run is not finished while it reports a FAIL.

## What is still yours

`facts.json` (which numbers and conclusions are worth stating, and their quotes), the report
prose and structure, the chart content (which skeleton, which rows), and every clinical judgment
about comparability. Everything else above is mechanical and already written.
