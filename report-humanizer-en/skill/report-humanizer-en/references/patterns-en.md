# English Report Expression Problem Checklist

**Usage:** This catalogue is a **checklist of clues, never a word blacklist**. Every hit goes back to context and asks: is this passage vague, redundant, ambiguous, or mismatched to report voice? If not, leave it alone. One word, one dash, one triad is never a reason to edit by itself.

**Severity marks:** **[strong]** = one sighting justifies an edit; **[weak]** = a single appearance does not constitute a reason to act; needs company from other hits in the same passage.

**Report-specific boundary:** Formal register, nominalization, and passive voice are legitimate in reports. Do not make rigorous prose chatty just to sound natural. The hard ban on process narration (Section 3 of SKILL.md) outranks every entry in this list.

---

## A. Structural (look at paragraph shape first, then sentences)

### A1. Staging before stating [strong]
Paragraph leads with "why this matters" before giving the actual content, opens on era filler ("In today's fast-paced landscape"), or explains the method before stating the conclusion.
**Before:** To better understand this drug's treatment positioning, we first review its mechanism of action before examining clinical evidence. It is an anti-PD-1 monoclonal antibody.
**After:** The drug is an anti-PD-1 monoclonal antibody.
**KEEP:** "For comparability, all values are taken from the same analysis timepoint." — Such calibration statements change how the reader interprets the data; keep once.

### A2. Process narration [strong] (the strongest report tell)
Writing for the reader to see your search, filtering, calculation, tools, and workflow. The test: are you talking about your work or about the facts (see SKILL.md Section 3).
**Before:** We searched 27 disclosures, removed 9 without endpoint data, and extracted endpoints from the remaining records line by line to reach the following conclusion: the regimen outperformed the control.
**After:** The regimen outperformed the control (18 of 27 disclosures contained comparable endpoints).
**KEEP:** "Data cutoff 2025-07-31, including 2 Phase III trials."

### A3. Self-explanation and choice rationale [strong]
Explaining why you wrote it this way, why you chose these items, what you hesitated over. This reasoning is process, not report content.
**Before:** The reason we selected only these two trials is that the other trials used inconsistent endpoint definitions and could not be compared; therefore, we can conclude the drug has an advantage in first-line treatment.
**After:** The drug outperformed the control in first-line treatment (limited to two Phase III trials with consistent endpoint definitions).
**Exception and wording:** A disclosure the host contract mandates (full text not retrieved, one record excluded, a definitional limit) must appear, but as a **property of the material** — "all four records in this batch are abstract-level, none full-text" is fine; "this run had no external network, the PubMed→PMC chain could not be started" describes working conditions and goes.

### A4. Inflated contrast (not X but Y) [strong]
Both halves add information, or the negative corrects a genuine misunderstanding → keep. Otherwise cut.
**Before:** This is not just a change in administration route but a paradigm shift in treatment philosophy: the drug switched from intravenous to subcutaneous injection.
**After:** The drug switched from intravenous to subcutaneous administration.
**KEEP:** "The difference comes from dosing intervals, not dose intensity."

### A5. Significance appended to facts [strong]
A fact followed by an evaluative clause, or each section ending with "this means…"
**Before:** The trial met its primary endpoint, marking a new shift in the treatment landscape and bringing new hope to patients.
**After:** The trial met its primary endpoint.
**KEEP:** "This is the first Phase III trial of this target to meet its primary endpoint."

### A6. Restating the heading [strong]
The sentence after a heading only repeats the heading, or explains how the document is organized.
**Before:** This section covers safety. The following describes the trial's safety data. Grade 3+ adverse event rate was 12%.
**After:** This section covers safety. Grade 3+ adverse event rate was 12%.

### A7. Reciting tables and figures [strong]
Prose repeats numbers already in the table, or a figure caption duplicates table data. Let the table or figure speak.
**Before:** As shown in the table below, median PFS was 9.4 months in the experimental arm, 6.1 months in the control arm, HR 0.62, p<0.001.
**After:** Experimental arm PFS was superior to control (HR 0.62, p<0.001).

### A8. Forced triads [weak]
Three parallel items used as a rhythm device rather than because the facts happen to be three.
**Before:** The drug offers three major advantages: efficacy, safety, and convenience.
**After:** The drug is effective, orally administered, with a Grade 3+ adverse event rate of 12%.
**KEEP:** "Export, search, and batch rename are three separate features."

### A9. Repeated sentence openings [weak]
Consecutive sentences start with the same subject or structure, purely to manufacture rhythm.

### A10. Paragraph-length balancing [weak]
Padding or cutting information to make each section visually equal in length.

---

## B. Wording and rhythm

### B1. Overused AI words [weak]
Delve, leverage, seamless, robust (figurative), underscore (verb), showcase (verb), testament to, pivotal, crucial, landscape (abstract noun), realm, tapestry (abstract noun), meticulous, enhance, intricate, vibrant, garner. These words are rare in real reporting, so two or three in one paragraph already justify an edit, but a single sighting is not a verdict: keep technical uses ("robust regression", "seamless handoff" in engineering).
**Before:** The drug brings a pivotal new landscape to this treatment realm, showcasing significant benefits and underscoring its crucial role.
**After:** The drug provides a new treatment option in this setting, with demonstrated efficacy in the Phase III trial.

### B2. Borrowed authority [strong]
"Industry experts believe," "studies show," "observers point out," "reports indicate" without naming the source.
**Before:** Industry experts believe this regimen is standard treatment.
**After:** This regimen is listed as first-line preferred by NCCN guidelines (citation).
**KEEP:** When the input already gives vague attribution, preserve its vagueness; do not invent a source.

### B3. Vague association [weak]
"Associated with," "connected to," "linked to," "related to," "ties to" without stating the actual relationship.
**Before:** The decline is associated with a change in the treatment landscape.
**After:** Enrollment fell after the 2024 guideline update moved the comparator to first line.

### B4. Stacked qualifiers [weak]
Repeated uncertainty at the same level ("may possibly," "to some extent approximately").
**Before:** The result may possibly suggest a potential trend toward benefit.
**After:** The result suggests a trend toward benefit (not statistically significant).
**KEEP:** "The difference may stem from baseline imbalance; causation is not confirmed."

### B5. Avoiding is/are/has [weak]
Using "serves as," "functions as," "possesses," "demonstrates" to sidestep direct statements.
**Before:** The drug possesses favorable safety characteristics.
**After:** The drug is safe, with a Grade 3+ adverse event rate of 12%.

### B6. Empty evaluation words [weak]
"Noteworthy," "worth attention," "promising," "impressive," "remarkable." If evaluating, give the basis; if you cannot, delete.
**Before:** The data is noteworthy.
**After:** This is the first 5-year OS data in this drug class.

### B7. Hyphenated pair invention [weak]
Inventing compound terms such as "R&D-production-commercialization integration" to replace existing definitions.
**Before:** The program spans R&D-commercial integration.
**After:** The program covers development and commercial launch planning.
**KEEP:** Established terms with specific meanings, such as "dose-response relationship" or "end-to-end encryption".

### B8. Em dash as universal connector [weak]
Repeatedly using em dashes to manufacture suspense or replace clause relationships. Keep those serving explanatory or parenthetical functions.

### B9. Passive voice and missing subjects [weak]
Text hides who acts or drops the subject. Use active voice when the actor is known and clarity matters.
**Before:** No configuration file is needed. Results are preserved.
**After:** You do not need a configuration file. The system preserves results.

### B10. Shallow -ing riders [weak]
Bolting an -ing phrase onto a simple fact: "highlighting," "underscoring," "reflecting," "demonstrating," "showcasing."
**Before:** The trial reached its endpoint, underscoring the drug's efficacy and highlighting its potential in this setting.
**After:** The trial reached its endpoint.

---

## C. Inflation, certainty and sales language

### C11. Inflated significance [strong]
"Marks a turning point," "sets the stage for," "reflects a broader trend," "plays a key role," "enduring legacy," "evolving landscape."
**Before:** The Statistical Institute was established in 1989, marking a pivotal moment in the evolution of regional statistics.
**After:** The Statistical Institute was established in 1989 as part of administrative decentralization.

### C12. Sales language [weak]
"Rich (figurative)," "profound," "nestled in," "breathtaking," "must-see," "stunning," "renowned for," "boasts," "features."
**Before:** The asset boasts a rich development history and a compelling clinical profile.
**After:** The asset has 4 completed Phase 2 trials and one Phase 3 trial in progress.

### C13. Certainty without evidence [weak]
Asserting outcomes or causation beyond what the source supports. "This will lead to," "ensures," "guarantees," "proves."
**Before:** The policy ensures improved patient outcomes.
**After:** The policy is expected to improve patient outcomes (projection based on pilot data).

### C14. Hedge stacks without stating judgment [weak]
Layers of uncertainty that never reach a conclusion: "appears to potentially suggest that it may…"
**Before:** The data appears to potentially suggest a possible benefit, though further investigation may be warranted.
**After:** The data suggest benefit, but the result did not reach statistical significance.

---

## D. Formatting by rule

### D15. Bold as decoration [weak]
Words bolded without reason; vertical lists with every item bolded and labeled.
**Before:** The readout includes **ORR**, **PFS**, and **OS**.
**After:** The readout includes ORR, PFS, and OS.

### D16. Decorative or Title Case headings [weak]
Headings capitalize every main word; headings or list items carry emojis or arrows (→) as decoration.
**Before:** ## Strategic Negotiations And Global Partnerships
**After:** ## Strategic negotiations and global partnerships

### D17. Curly quotation marks [weak]

### D18. Mixed notation — one value, two forms [weak]
The same report writes `10·3 months` beside `11.1 months`, or `64%` beside `64 %`. Source material mixes these forms, so copying it through leaves a trace; the unifying changes typography only, never the value or digit count. It also spares the reader wondering whether the two forms carry different definitions.
**Before:** median PFS 11·1 months (95% CI 9·9–NE), grade ≥3 haemorrhage 2 %
**After:** median PFS 11.1 months (95% CI 9.9–NE), grade ≥3 haemorrhage 2%
**Boundary:** quotes, code, IDs, URLs and tables (prose and lists only when the host protects tables) stay as they are; no thousands separators or units added on your own.
Curly quotes ("…") where the format uses straight quotes ("..."). Most editors auto-curl, so this is weak alone.

---

## E. Leftovers

### E18. Chatbot residue [strong]
"I hope this helps," "Great question," "Of course," "Certainly," "Let me know," "Would you like me to…," "Should I continue?"
**Before:** Great question! Here is an overview of the trial. Let me know if you'd like me to expand.
**After:** The trial enrolled 847 patients with advanced NSCLC who progressed on platinum-based chemotherapy.

### E19. Knowledge-limit disclaimers and guesses [strong]
Mentioning where the model's knowledge ends, or admitting no source then filling the gap with a guess.
**Before:** While specific founding details are not extensively documented, the company appears to have been established in the 1990s.
**After:** The company's founding date is not documented. (Or omit the sentence.)

### E20. Writing about the document [strong]
"This section is organized by…," "The table below compares…," "Was added to replace…," "Compiled from…"
**Before:** The figures below are drawn from published pricing; unconfirmed items are flagged rather than guessed.
**After:** Prices are each vendor's published rate. Two vendors publish nothing; call them.

---

## F. Wrong reader

### F21. Re-explaining what the reader knows [strong]
Short reply restates the problem, walks through diagnosis, and buries the decision in the last line.
**Before:** You asked whether the asset is worth in-licensing, so let me walk through the data. We reviewed the Phase 2 readouts first, then compared them to the standard of care. The Phase 2 trial showed a 42% ORR, and the asset is not just a pipeline addition but a potential franchise, so on balance the answer is yes, subject to the caveat that the Phase 3 readout is still pending.
**After:** The asset is worth pursuing, subject to the pending Phase 3 readout. The Phase 2 trial reported a 42% ORR versus roughly 25% for the current standard of care.

---

## G. Report-specific

### G22. Recounting the search or tooling [strong]
Describing how you searched, what tools you used, or how you standardized data.
**Before:** We standardized endpoint definitions across sources using a controlled vocabulary and extracted data for each trial.
**After:** (State the finding or conclusion; mention standardization only if it affects interpretation.)

### G23. Unlabeled certainty or unlabeled uncertainty [weak]
Presenting exploratory or subgroup analyses as primary conclusions, or stating planned work as completed.
**Before:** The drug improved OS in the subgroup analysis.
**After:** The drug improved OS in a prespecified subgroup analysis of patients with high PD-L1 expression (exploratory endpoint).

### G24. Sections ending with significance instead of evidence [weak]
Each section closes with "This suggests future potential" rather than the last piece of evidence.
**Before:** Median PFS was 9.4 months. This underscores the drug's potential in this setting.
**After:** Median PFS was 9.4 months.

### G25. "Studies show" with no source [strong]
Generic plural reference without attribution.
**Before:** Studies show this combination is effective.
**After:** Two Phase III trials (NCT12345, NCT67890) demonstrated efficacy of this combination.

### G26. Numbers without a cut-off or denominator [weak]
Presenting absolute counts without the base or threshold that gives them meaning.
**Before:** 42 patients experienced Grade 3+ adverse events.
**After:** 42 of 150 patients (28%) experienced Grade 3+ adverse events.

---

## After a hit, how to fix

1. **Rewrite the paragraph around its point** instead of patching flagged phrases one by one. Then check that numbers and qualifiers survived.
2. **Delete only filler or process.** Every fact, caveat, qualifier, and source must remain in the prose.
3. **Re-read asking:** Does this still sound like "reporting my work"? If yes, continue deleting process narration.
4. **When a paragraph hits 3+ patterns,** the problem is usually structure, not wording.

## Relation to the mechanical scanner

`scripts/tell-scan.py` (SKILL.md Section 8) is a separate mechanical layer. Its `S-PROC-*`, `S-INFL-*`, `S-STRUCT-*` and `W-*` identifiers do not map one to one onto the entries above: `S-PROC-01..07` cover A2, A3, A6, E18 and G22 together, `S-INFL-01..04` cover A4, A5, B1, B2, B6 and C11-C14, `S-STRUCT-01..04` cover A6, A7 and G24, and `W-*` covers B3, B4, B8, B10, D15, D16, D17, D18, E18 and the document-level counts (three or more em dashes, eight or more bold spans, `W-FMT-MIXED` mixed notation). Use the scanner to find candidates and this catalogue to decide.
