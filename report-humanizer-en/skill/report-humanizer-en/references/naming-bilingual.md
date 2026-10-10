# Bilingual Entity, Term, and Drug Naming Rules

The goals are simple: **one form for the same entity throughout the document**; **never invent a name that cannot be supported**.

## 0. Total flow

```text
A name enters the prose
  -> confident common-knowledge English/Chinese pair: use it directly
  -> uncertain or ambiguous:
       -> host-returned paired fields: use the returned value
       -> one dictionary lookup (at most two lookups): take the standard name
       -> if still unresolved: use the directional fallback; never invent
  -> same-name entities: disambiguate using the report's own context
     (originator, target, indication, and stage), and use one consistent entity
```

Do not translate a name merely because the report is bilingual. First decide whether
it is a settled pair; then use the host data or one lookup only when the pair is not
certain. A same-name candidate must fit the report's own evidence and context.

## 1. Common sense first

The following INN pairs are settled knowledge. Use a pair directly when certain; do
not spend a tool call on it. Never guess when uncertain: move to Section 2 instead.

| INN | Chinese |
| --- | --- |
| pembrolizumab | 帕博利珠单抗 |
| nivolumab | 纳武利尤单抗 |
| bevacizumab | 贝伐珠单抗 |
| trastuzumab | 曲妥珠单抗 |
| osimertinib | 奥希替尼 |
| adagrasib | 阿达格拉西布 |
| sotorasib | 索托拉西布 |
| docetaxel | 多西他赛 |
| lenalidomide | 来那度胺 |
| semaglutide | 司美格鲁肽 |
| atezolizumab | 阿替利珠单抗 |
| durvalumab | 度伐利尤单抗 |

The test is whether the correspondence is certain, not whether one spelling seems
familiar. If there is any meaningful doubt, do not guess a Chinese or English name.

## 2. Dictionary lookup (one or two times only)

Use the first available method below. Prefer a value already returned by the host
project; otherwise choose one suitable dictionary method. Do not use every tool for
the same term.

1. **Paired fields already returned by the host project (preferred; no extra call).**
   Examples include `arms.drugs.drug_earth_name_en` /
   `arms.drugs.drug_earth_name_cn`, and `arms.drugs.drug_earth_all_name` for
   synonyms and disambiguation. Other paired fields include `indication_name_en`,
   `company.short_name_en`, `modality.name_en`, and
   `clinical_endpoint.endpoint_en`. Use the returned value instead of translating.
2. **TS report projects:** call `report-query-drug` with `drug_names` set to the
   source name and `is_en` set to switch Chinese or English output.
3. **Pharmcube MCP:** call `pharmcube-mcp-drugBaseLiteCN` with `drugName`, and the
   required `pageNo` and `pageSize`; use returned `name_short` and
   `drug_name_synonyms`.
4. **Linking API:** use the `drug` entity for standardized names and synonyms.

Look up a term ONCE, at most twice. Never chain-probe across tools, spellings, or
languages. If the result gives multiple candidates, choose the candidate consistent
with the report context: originator, target, indication, and stage, rather than the
most popular candidate. Never merge two different drugs.

## 3. Directional fallback

When the dictionary returns nothing usable, preserve information without inventing a
translation. The fallback is directional and applies to drug names and other names
where no verified correspondence is available.

| Direction | Write this | Never do this |
| --- | --- | --- |
| English -> Chinese | **KEEP THE ENGLISH NAME** | No transliteration, no invented Chinese name, no invented Chinese abbreviation, no literal translation |
| Chinese -> English | **USE PINYIN**, optionally bracketing the Chinese original at first mention | No invented English name, no literal gloss, no substitution with a similar-sounding drug |

For example, if `zongertinib` has no verified Chinese correspondence, keep
`zongertinib`. If a Chinese colloquial name has no verified English correspondence,
use pinyin and optionally add the Chinese original at first mention. Do not turn a
brand name into a generic name: keep whichever name the source used, and bracket the
other only when it helps.

## 4. Other entities

- **Trial names and registration numbers:** copy `KEYNOTE-189`, `NCT02576574`, and
  `ChiCTR2000031495` verbatim. Preserve case and spacing; never reorder, zero-pad,
  or re-case them. Use one form throughout.
- **Sponsoring companies:** prefer the standard short form; the full name is optional
  at first mention. Use `short_name_en` when the host has returned it.
- **Targets:** use one standard form throughout, such as `PD-1`, `VEGF-A`, or `EGFR`.
  Do not alternate between a target symbol and an expanded variant without reason.
- **Endpoints:** spell out `PFS`, `OS`, `ORR`, `DCR`, `DoR`, `AE`, and `SAE` at first
  use, then use one form throughout. Keep abbreviation case unchanged.
- **Diseases and pathologies:** use the standard name in the report's language; add
  the other language in brackets only when needed. Do not alternate between a full
  disease name and an abbreviation as competing main forms.
- **Clinical stages and lines of therapy:** use forms such as `Phase III`,
  `first-line`, and `second-line and beyond`, consistently throughout.
- **Adverse-event grades:** preserve grades as written in the source; do not convert,
  normalize, or infer a grade.

## 5. Format consistency

- Use Arabic numerals throughout.
- Use one percentage and interval format document-wide, for example `9.4 months`,
  `0.62 (95% CI 0.48-0.80)`, and `p<0.001`.
- For Latin/Chinese spacing, follow the document's existing convention. Do not
  alternate between spaced and unspaced forms from sentence to sentence.
- Define abbreviations at first use, except in table headers. After definition, use
  one abbreviation or one full form consistently rather than ping-ponging between
  aliases.
