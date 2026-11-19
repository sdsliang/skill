#!/usr/bin/env python3
"""Fill ``drug`` / ``target`` on a watchlist from the platform's ``clinical_result.arms``.

Why this exists: ``clinical_result.arms[].drugs[]`` is the only structured drug/target
source the result tool exposes — there is no ``base.trial_drug`` and no
``clinical_result.drug`` anywhere in its 75-name ``selected_fields`` whitelist. The
shipped skill lets the judging model write ``drug``; when it forgets, every card face
comes out empty (v0.15 ADA run: 27/27 empty).

Picking rule, deterministic on purpose (a combination trial lists the comparator's
drug in its own arm, so "first drug in the payload" is wrong):

  1. split the title at the first ``vs`` / ``versus`` — the head segment names the
     experimental agent, the tail names the comparator;
  2. prefer the first candidate that occurs in the head segment;
  3. otherwise take the first candidate in document order;
  4. targets come from *that* drug record only, so the comparator's targets do not
     leak onto the card;
  5. when the drug is known by an INN but the abstract identifies it by a code
     (``enicepatide`` / ``CT-388``), print the code in parentheses.

Rows where arms carries nothing are patched by hand and marked ``drug_from=manual``.
Usage:  attach_arms.py <watchlist.json> <arms.json> <out.json>
"""
import json
import re
import sys

WL, ARMS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W = json.load(open(WL, encoding="utf-8"))
A = json.load(open(ARMS, encoding="utf-8"))

# arms returned no drug at all for these five; the agent is named in the abstract text.
MANUAL = {
    "24_37_f5069c3eb96d8c926d8e4a38d664d75f_1": ("司美格鲁肽 semaglutide", ["GLP-1R"]),
    "24_37_a7b39fdd511509db34b9ad0396fac896_1": ("ZT006", ["GLP-1R"]),
    "24_37_d978fbb40cf9a2e383b946169895c7ff_1": ("卡介苗 BCG", []),
    "24_37_4c45993879169ae98e6236f06855bede_1": ("卡介苗 BCG", []),
    "24_37_dc91b55b08a67ef8e278bd6e4844db73_1": ("二甲双胍 metformin", []),
}

VS = re.compile(r"\bvs\.?\b|\bversus\b", re.I)
CODE = re.compile(r"\b[A-Z]{2,4}-?\d{2,5}\b")


def candidates(arms):
    """Distinct drug records in payload order, cn name first, with their own targets."""
    out, seen = [], set()
    for d in arms.get("drugs", []):
        cn, en = (d.get("cn") or "").strip(), (d.get("en") or "").strip()
        name = cn or en
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tg = [t for t in (d.get("targets") or []) if t]
        # match on either language: abstracts are English, arms often only has cn
        names = [x for x in (cn, en) if x]
        out.append({"name": name, "names": names, "targets": tg})
    return out


for c in W["cards"]:
    arms = A.get(c["esid"]) or {}
    cands = candidates(arms)
    title = c.get("title") or ""
    m = VS.search(title)
    head = title[: m.start()] if m else title
    chosen, src = None, "arms"
    low = head.lower()
    for cand in cands:
        if any(n.lower() in low for n in cand["names"]):
            chosen = cand
            break
    if chosen is None and cands:
        chosen = cands[0]
    if chosen is None and c["esid"] in MANUAL:
        name, tg = MANUAL[c["esid"]]
        chosen, src = {"name": name, "names": [name], "targets": tg}, "manual"

    if chosen:
        name = chosen["name"]
        # INN with a code in the title (enicepatide / CT-388): print both, code last
        if name.lower() not in title.lower():
            for code in CODE.findall(title):
                name = f"{name} ({code})"
                break
        c["drug"] = name
        if chosen["targets"] and not c.get("target"):
            c["target"] = " / ".join(chosen["targets"][:3])
    c["drug_from"] = src if chosen else "none"

W["_review_meta"] = {
    "source_watchlist": WL,
    "drug_target_source": "clinical_result.arms[].drugs[] (platform tool); "
                          "manual patch for 5 rows where arms is empty",
}
json.dump(W, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{OUT} · drug filled {sum(1 for c in W['cards'] if c.get('drug'))}/{len(W['cards'])} · "
      f"arms={sum(1 for c in W['cards'] if c.get('drug_from') == 'arms')} "
      f"manual={sum(1 for c in W['cards'] if c.get('drug_from') == 'manual')} "
      f"none={sum(1 for c in W['cards'] if c.get('drug_from') == 'none')}")
