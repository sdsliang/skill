# ASCO 2026 Conference Clinical Interpretation

This report is built from the public research abstracts of this year's meeting, pulled through the Tool Smith platform tool `pharmcube-query-clinical-result-with-params`: **1,639 abstracts, deduplicated by study**, one per `clinical_result_extra_esid`.

The counting unit is the **number of research abstracts**. An abstract that covers several cancer types, drugs or regions is counted once in each of those views, so column totals usually exceed 1,639 and shares can add up to more than 100%. They must not be summed into a composition. Unless stated otherwise, **every rate is over 1,639 abstracts**.

One caveat has to come first: the platform's `research_institute_*` field records the **current holder** of a drug, not its original developer. Holders of generic backbone chemotherapies such as carboplatin, paclitaxel, gemcitabine and oxaliplatin are therefore pushed to the top of that ranking. Read it together with the drug chart when judging the innovator landscape.

## Act 1 · The meeting at a glance

Scale, tempo, geography: how many abstracts, when they dropped, and whose turf it is. Every later act builds on this screen.

Disclosure clusters on three dates: 510 abstracts on 21 May, 464 on 30 May, 327 on 1 June and 273 on 31 May; all other dates together account for less than 5%. Information density is not uniform — 30 May and 1 June are the days the abstract bodies are released, while 21 May is a titles drop, so the same studies appear twice and must not be read as two different cohorts.

::visualization[Disclosure tempo by date]{path="/workspace/visualizations/rank-day-bar-en.json"}

Only 49 abstracts are flagged as LBA (Late-Breaking Abstract), 3.0% of the total, 15 of them China-based — this is the part of the meeting that actually carries new data, and it gets the heaviest weight when Act 5 screens for actionable signals{{ref_1}}.

Ranked by sponsor registration country, China accounts for 425 abstracts and the United States for 394, together close to half the meeting. Brazil follows with 54, France 14, Korea 14, Italy 13 and Japan 10, with a very long tail. This view only counts abstracts that can be attributed to a sponsor; records without one do not appear and are not evidence that no sponsor exists.

::visualization[Where the research sits]{path="/workspace/visualizations/rank-country-bar-en.json"}

## Act 2 · Where the heat is, and how mature the evidence is

Cancer type and disease domain show what everyone is chasing; stage, evidence type and overall evaluation show how hard what they caught actually is. Read the two hands together to see which conclusions travel and which are early signals.

The most-disclosed cancer types are solid tumours with 141 abstracts and non-small cell lung cancer with 137, followed by colorectal cancer 92, breast cancer 88, gastric cancer 70, melanoma 65, hepatocellular carcinoma 56, HR-positive breast cancer 56, ovarian cancer 52, head and neck squamous cell carcinoma 50, HER2-positive breast cancer 50 and small cell lung cancer 49. The head does not monopolise the field: beyond the top 12 there is a large population of single-indication studies, which is the shape of "solid tumours as the base, lung cancer leading, GI and breast following". Lung cancer deserves a separate look because it carries both confirmatory phase 3 studies and a dense layer of phase 1/2 combinations at the same meeting{{ref_2}}.

::visualization[Most-disclosed cancer types]{path="/workspace/visualizations/rank-indication-bar-en.json"}

By platform disease-domain tags, oncology covers almost the whole meeting with 1,619 abstracts; rare disease (Europe) 579, rare disease (US) 478, haematology 197 and rare disease (China) 156 form the second layer. An abstract can carry several domain tags, so these columns cannot be added. The frequency of rare-disease tags reflects that many oncology studies are also registered as the matching rare tumour — the rare-disease column is not a separate set of non-oncology research.

::visualization[Disease domain mix]{path="/workspace/visualizations/rank-domain-bar-en.json"}

The stage mix is lopsided: advanced 516 abstracts, locally advanced 125, phase III 109, phase II 61, phase IV 54 and early stage 47. Advanced plus locally advanced take more than 60%, which means most of the meeting studies metastatic or unresectable populations; only 47 abstracts target cure-oriented early-stage disease, a clear scarcity slot.

::visualization[Study stage]{path="/workspace/visualizations/rank-stage-bar-en.json"}

Evidence type says more about maturity: phase II leads with 469 abstracts, retrospective research 409, real-world research 364, phase I 246, prospective research 239, phase III 179 and phase I/II 152. Phase III is only 10.9%, while retrospective and real-world work together reach 773 — a large share of this year's "results" are re-analyses of existing data rather than new readouts of new drugs. The 246 phase I abstracts are an early asset pool invisible from the outside and worth filtering by target{{ref_3}}; real-world and retrospective work, by contrast, mostly appears in later-line and off-label settings here, so confirm the comparator before accepting a positive finding{{ref_4}}.

::visualization[Evidence type]{path="/workspace/visualizations/rank-evidence-source-bar-en.json"}

Overall evaluation: positive 1,248 abstracts (76.1%), negative 147 (9.0%), terminated 12, not assessed 229, and 3 unlabelled. The 76.1% positivity rate is not the industry's true success rate — abstracts that get written up are themselves a selected sample, and trials that failed or stopped usually never appear here. Using 1,248 as the numerator systematically overstates success.

::visualization[Overall evaluation]{path="/workspace/visualizations/rank-evaluation-bar-en.json"}

Crossing stage with evaluation makes the structure clearer: positive results concentrate in advanced populations (390 abstracts), then locally advanced 101, phase III 80, phase II 41, phase IV 40 and early stage 34; negative results are also mostly advanced (42), with phase III 16 and locally advanced 10. In other words, **the advanced population is both the largest testing ground and the largest failure ground**; early-stage samples are still too small to judge success or failure.

::visualization[Stage × evaluation]{path="/workspace/visualizations/matrix-stage-evaluation-en.json"}

## Act 3 · Who runs the research, who holds the asset

The sponsor is "who ran this study", the drug originator field is "who owns the drug", and the two are usually not the same company. Then look at how concentrated targets, drugs and mechanisms are, and at the cancer type → target → drug pathway.

The sponsor ranking is led by academic centres: Fudan University 28 abstracts, National Cancer Institute 24, Sun Yat-sen University 23, MD Anderson 23; on the industry side AstraZeneca 23, Hengrui Pharma 15, Pfizer 14, Roche 13. Investigator-initiated work outnumbers industry-sponsored registration studies, which makes this the most misread chart of the meeting — it counts who does the work, not who sells the drug.

::visualization[Leading sponsors]{path="/workspace/visualizations/rank-sponsor-bar-en.json"}

Switch to the asset-ownership lens and the picture inverts: Roche 289 abstracts, Merck & Co. 227, Cheplapharm 203, Bristol Myers Squibb 153, Sanofi 149, Eli Lilly 142, AstraZeneca 139, Pfizer 127, with BeiGene entering at 102. Much of Roche's 289 comes from backbone chemotherapies it holds (fluorouracil, capecitabine, bevacizumab), and Cheplapharm and takata-seiyaku rank high purely through generic holdings — **this chart reads "whose books the asset sits on", not "who innovates"**. Read innovation intensity together with the external-sponsorship chart and the drug chart.

::visualization[Leading drug originators]{path="/workspace/visualizations/rank-institute-bar-en.json"}

Isolating the studies where the sponsor and the drug's originator have no overlap at all answers a different question: who runs external validation on someone else's asset. Roche 117, Cheplapharm 89, Merck & Co. 77, Eli Lilly 73, Sanofi 70, BMS 68, with Hengrui 56 and BeiGene 47 also on the list. These are usually investigator-initiated combinations or real-world validations — free indication-expansion evidence for the asset owner, and the earliest window into "how others use this drug" for anyone tracking it.

::visualization[Originators most studied by outside sponsors]{path="/workspace/visualizations/rank-institute-external-bar-en.json"}

Targets are highly concentrated: PD1 442 abstracts, DNA 405, microtubule 207, TYMS 189, PDL1 139, EGFR 98, HER2 97, DNA polymerase 96, c-Kit 94, CTLA4 85. PD1 and PDL1 together reach 581 and remain the largest common channel; the high position of DNA, microtubule and TYMS reflects that chemotherapy is still the backbone of combination regimens, not that these are hot new targets.

::visualization[Most-disclosed targets]{path="/workspace/visualizations/rank-target-bar-en.json"}

Drug chart: pembrolizumab 162 abstracts, oxaliplatin 119, fluorouracil 93, carboplatin 89, nivolumab 85, cisplatin 85, paclitaxel 77, folinic acid 72, capecitabine 71, gemcitabine 69. Two of the top three are chemotherapy agents, which shows how often the comparator in this meeting's studies is the standard platinum backbone; pembrolizumab's position comes both from new indications and from being cited as the comparator arm again and again{{ref_5}}.

::visualization[Most-disclosed drugs]{path="/workspace/visualizations/rank-drug-bar-en.json"}

Mechanism mix: small molecules 1,015 abstracts, monoclonal antibodies 658, platinum agents 289, taxanes 183, antibody-drug conjugates 155, bispecific antibodies 128, nucleoside analogues 115, radiosensitisers 86. ADCs plus bispecifics reach 283 and now exceed platinum — the clearest technology migration of the meeting.

::visualization[Mechanism of action mix]{path="/workspace/visualizations/rank-moa-bar-en.json"}

Chaining the three layers shows the pathway clearly: the PD1 channel is used by 25 abstracts in colorectal cancer, while the solid-tumour side splits across microtubule, TYMS and DNA backbones. Crowding is highest for PD1 in GI tumours — one target combined 25 times in one cancer type, so differentiation can only come from the combination partner and the population{{ref_6}}. Every link opens the matching abstract list.

::visualization[Cancer type → target → drug]{path="/workspace/visualizations/flow-indication-target-sankey-en.json"}

## Act 4 · China's voice

Under one hard rule — the sponsor is registered in mainland China, Hong Kong, Macau or Taiwan — China accounts for 425 abstracts, 25.9% of the meeting. That is the only criterion: Chinese subsidiaries of multinationals count at their registration location and are not merged into the parent, and abstracts without a sponsor cannot be attributed and are excluded from either side.

China's cancer-type mix differs sharply from the rest of the world: gastric cancer 37 abstracts, NSCLC 35, colorectal 34, solid tumours 33 and gastro-oesophageal junction 27, with a much heavier GI weight than the global picture (rest of world: solid tumours 108, NSCLC 102, breast 82, melanoma 61, colorectal 58). Chinese investigators put their resources into gastric, colorectal and GEJ cancers, which are highly prevalent locally, and invest relatively less in breast cancer and melanoma.

::visualization[Cancer type × China / rest of world]{path="/workspace/visualizations/matrix-china-indication-en.json"}

China's target ranking shows the same two peaks of PD1 plus chemotherapy backbone: PD1 161 abstracts, DNA 140, TYMS 81, microtubule 72, VEGFR2 43. Compared with the rest of the world, VEGFR2 (the anlotinib and apatinib family) is used far more densely in China, a direct projection of domestic multi-kinase small molecules.

::visualization[Targets most concentrated in China-led work]{path="/workspace/visualizations/rank-china-target-bar-en.json"}

Who leads: Fudan University 25 abstracts, Sun Yat-sen University 19, Hengrui Pharma 13, West China Hospital 13, Sun Yat-sen University Cancer Center 10. The list is almost entirely universities and affiliated hospitals, so China's voice is first of all the voice of **investigator-initiated research**; on the industry side Hengrui, Baili-Bio, Akeso and Zelgen enter with phase 3 assets, but not yet in numbers that change the shape of the ranking.

::visualization[China-based sponsors]{path="/workspace/visualizations/rank-china-sponsor-bar-en.json"}

China's evidence maturity deserves its own note: evidence type is phase II 218 abstracts, prospective research 117, phase I 79 and phase I/II 47, with far fewer retrospective studies than the rest of the world (407 there); stage is advanced 129, locally advanced 47, phase III 34 and phase II 24. China leans towards prospective, phase II-heavy designs with modest sample sizes but disciplined conduct, rather than backfilling with real-world data.

The positivity gap is the widest single difference: 96.5% positive in the China cohort versus 69.0% elsewhere, and 2.1% negative versus 12.4%. That gap cannot be read directly as higher quality — most likely it is three things stacking: negative results are less often written up as abstracts, China's mix is heavier in single-arm phase II without randomisation, and the meeting's China work concentrates on targets that are still unproven, where early signals are easily judged positive. China holds 15 of 49 LBAs (about 31%), above its 25.9% share of the total, so the weight of the headline data is rising{{ref_7}}.

Three representative examples: benmelstobart plus chemotherapy and anlotinib as first-line treatment of advanced non-squamous NSCLC in a phase 3 trial{{ref_8}}; M701 (a CD3/EpCAM bispecific) given intraperitoneally for malignant ascites in a phase 3 trial{{ref_9}}; and a randomised study of neoadjuvant chemoradiotherapy versus neoadjuvant chemotherapy followed by D2 gastrectomy in gastric cancer{{ref_7}}. What the three share is **adding to or subtracting from an existing standard of care** rather than opening a brand-new mechanism — which explains both China's high positivity rate and the continued scarcity of genuinely novel mechanisms.

## Act 5 · Which few readouts can change a decision

This act carries no chart, only a list. The screening rule is reproducible: evaluation positive and key evidence present, then weighted by LBA (+3), phase III in the title (+2), advanced or locally advanced (+1), a named target (+1) and a stated primary endpoint (+1), finally deduplicated by first drug × first cancer type. Of 1,639 abstracts, 586 enter the candidate pool and 502 remain after deduplication, ranked by score:

1. **Tunlametinib plus vemurafenib**, BRAF V600E-mutant metastatic colorectal cancer, phase 3 randomised, primary endpoint median PFS, LBA. Kezhou Pharma. One of the few phase 3 confirmatory targeted combinations in GI cancer at this meeting.
2. **Benmelstobart plus anlotinib plus chemotherapy**, first-line advanced non-squamous NSCLC, phase 3 randomised, primary endpoint median PFS, LBA. Chia Tai Tianqing. The immuno + anti-angiogenic + chemotherapy triplet keeps accumulating in first-line NSCLC.
3. **iza-bren (izalontamab brengitecan)**, unresectable locally advanced or metastatic triple-negative breast cancer, phase 3, co-primary median PFS and median OS, LBA. Baili-Bio. A domestic ADC going head to head with physician's choice chemotherapy in TNBC is the heaviest single China asset at this meeting{{ref_10}}.
4. **ADAM: adjuvant avelumab**, Merkel cell carcinoma with lymph node metastases, phase 3 randomised double-blind placebo-controlled, primary endpoint recurrence-free survival, LBA. The first phase 3 evidence for adjuvant immunotherapy in a rare skin tumour.
5. **RAMPART: adjuvant durvalumab**, resected primary renal cell carcinoma, phase 3 randomised, primary endpoint disease-free survival, LBA. Perioperative immunotherapy keeps moving earlier, into the post-surgery disease-free population.
6. **Chiauranib plus weekly paclitaxel**, platinum-resistant or refractory ovarian cancer, phase 3, LBA. Chipscreen. An anti-angiogenic small molecule reaches phase 3 in the later-line ovarian setting.
7. **SARC041: abemaciclib versus placebo**, dedifferentiated liposarcoma, phase 3 randomised double-blind. A CDK4/6 inhibitor entering sarcoma, a rare new-indication direction at this meeting.
8. **A real-world analysis of first-line maintenance in NSCLC** (post-hoc analysis of phase 3 data) — low score but highly readable: it tells you how the drug is actually used in practice{{ref_4}}.

Two warnings when reading the list: the score is a proxy for actionability, not for clinical value; and one abstract is one disclosure — a positive phase 3 still has follow-up and regulatory distance to market. What genuinely deserves a reminder are items 1, 2, 3 and 6: they carry phase 3, LBA and a defined endpoint at once, and all four are tied to Chinese assets{{ref_5}}.

## Act 6 · What is collapsing, what is blank, whom to watch

Negative and terminated studies total 159 abstracts. Concentration is low but the direction is clear: breast cancer 14, NSCLC 13, colorectal 8, HER2-positive breast cancer 8, HR-positive breast cancer 8, gastric cancer 7, melanoma 7, solid tumours 7. Breast cancer produces negative results in three subtypes at once, making it the single most failure-prone disease area this year.

::visualization[Where negative and terminated results concentrate]{path="/workspace/visualizations/rank-negative-indication-bar-en.json"}

The attribution boundary has to be stated: the platform has no separate safety or efficacy item fields, so what follows is generalised from titles and key-evidence text, not a structured conclusion. Three failure patterns are distinguishable — first, losing the comparator on the endocrine line, with giredestrant plus palbociclib versus letrozole plus palbociclib as the textbook case{{ref_11}}; second, immuno-combinations failing to beat the comparator in unselected advanced populations, and one of this year's 12 terminated records is exactly such a phase 3 immuno-combination study{{ref_12}}; third, later-line single-arm studies judged negative, which is insufficient efficacy rather than a design failure.

::visualization[Summary]{path="/workspace/visualizations/summary-callout-en.json"}

Blanks matter more than collapses: 229 abstracts (14.0%) not assessed, 147 negative, 12 terminated and 3 unlabelled — 391 in total (23.9%) in an open information state, published but without a readout you can act on. Add 6.1% (100 abstracts) with no usable target annotation, 6.1% (100) with no disclosed drug and 36.4% (597) that cannot be attributed to a sponsor, and the field-level gaps cluster in three places — no presentation-level field (oral / poster / LBA session), no separate safety items, and incomplete entity-ID coverage. All three cap how far a conclusion can be traced back to the evidence.

Assets and events worth a 6–12 month reminder:

- Tunlametinib plus vemurafenib (BRAF V600E mCRC): phase 3 PFS is out; watch OS maturity and the NDA timeline.
- iza-bren (TNBC): dual phase 3 endpoints PFS and OS; watch the full OS curve and the safety summary.
- Benmelstobart plus anlotinib (1L non-squamous NSCLC): access and reimbursement path for the triplet.
- M701 (CD3/EpCAM bispecific, malignant ascites): the registration strategy for local delivery decides how much room bispecifics have in intracavitary therapy.
- Hengrui, BeiGene and Akeso are the most-cited originators by outside sponsors this year (56 / 47 / 26 abstracts). The more external validation an asset gets, the cheaper its next indication expansion, so read their real-world data first.

In one line: the certainty this year sits in **continued reinforcement of the chemotherapy backbone and the PD1 channel**, the variable sits in **phase 3 readouts for ADCs and bispecifics**, and China's voice is moving from a share of volume to a share of LBAs — while genuinely novel mechanisms remain scarce.
