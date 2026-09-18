"""Offline full-text evidence: article metadata, never filenames or citation self-agreement.

The trust boundary is an archived source response, not cryptographic authenticity. No
network calls are made. JATS article-meta provides the PMID/PMCID pair; JSON mapping
responses can supply that pair for plaintext. Reference-list IDs cannot identify a body.
"""
import glob
import json
import os
import re
import xml.etree.ElementTree as ET


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def inspect(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    result = {"name": os.path.basename(path), "text": text, "pmid": set(), "pmcid": set(),
              "body": "", "valid": False, "xml": False,
              "claimed_pmid": set(), "claimed_pmcid": set()}
    start = text.find("<article")
    if start >= 0:
        result["xml"] = True
        try:
            root = ET.fromstring(text[start:])
        except ET.ParseError:
            return result
        meta = root.find("./front/article-meta")
        if meta is not None:
            for node in meta.findall("article-id"):
                kind, value = node.get("pub-id-type"), (node.text or "").strip()
                if kind == "pmid" and re.fullmatch(r"\d+", value):
                    result["pmid"].add(value)
                if kind in ("pmcid", "pmc") and re.fullmatch(r"(?:PMC)?\d+", value, re.I):
                    result["pmcid"].add("PMC" + re.sub(r"^PMC", "", value, flags=re.I))
        body = root.find("body")
        if body is not None:
            result["body"] = " ".join(body.itertext())
        result["valid"] = len(compact(result["body"])) >= 40
        return result
    # Plaintext IDs must be in its header, not an arbitrary bibliography number.
    head = text[:2000]
    result["claimed_pmcid"] = {x.upper() for x in re.findall(r"\bPMC\d+\b", head, re.I)}
    result["claimed_pmid"] = set(re.findall(r"\bPMID\s*[:=]?\s*(\d+)\b", head, re.I))
    result["body"] = text
    result["valid"] = (len(compact(text)) >= 200 and bool(re.search(
        r"\b(?:Results|Methods|Discussion)\b", text, re.I)))
    return result


def evidence(art, run_dir=None):
    paths = [p for p in glob.glob(os.path.join(art or "", "sources", "**", "*"), recursive=True)
             if os.path.isfile(p) and os.path.getsize(p) < 20_000_000]
    bodies, mappings = [], set()
    # Archived web_fetch returns are independent mapping receipts too. Only structured
    # PMID/PMCID pairs count; tool arguments, execute scripts and prose assertions do not.
    receipt_objects = []
    if run_dir:
        from history import target_messages
        try:
            messages, _ = target_messages(run_dir)
            receipt_objects = [part for message in messages if message.get("kind") == "request"
                               for part in message["parts"] if isinstance(part, dict)]
        except (ValueError, OSError, TypeError, AttributeError):
            pass  # Unscoped/malformed receipts provide no corroboration.
    def mapping_walk(o):
        if isinstance(o, dict):
            pmid = o.get("pmid") or (o.get("id") if o.get("source") == "MED" else None)
            pmcid = o.get("pmcid")
            if re.fullmatch(r"\d+", str(pmid or "")) and re.fullmatch(r"PMC\d+", str(pmcid or "")):
                mappings.add((str(pmid), pmcid))
            for v in o.values():
                mapping_walk(v)
        elif isinstance(o, list):
            for v in o:
                mapping_walk(v)
    for obj in receipt_objects:
        if obj.get("part_kind") != "tool-return" or obj.get("tool_name") != "web_fetch":
            continue
        text = obj.get("content")
        if isinstance(text, str):
            # A fetch preview may precede a structured source response.
            for match in re.finditer(r"\{", text):
                try:
                    parsed, _ = json.JSONDecoder().raw_decode(text[match.start():])
                    mapping_walk(parsed)
                except ValueError:
                    pass
        else:
            mapping_walk(text)
    for path in paths:
        text = open(path, encoding="utf-8", errors="replace").read()
        # Independently archived structured source mapping (e.g. Europe PMC response).
        try:
            obj = json.loads(text)
        except (ValueError, TypeError):
            obj = None
        def walk(o):
            if isinstance(o, dict):
                pmid = o.get("pmid") or (o.get("id") if o.get("source") == "MED" else None)
                pmcid = o.get("pmcid")
                if re.fullmatch(r"\d+", str(pmid or "")) and re.fullmatch(r"PMC\d+", str(pmcid or "")):
                    mappings.add((str(pmid), pmcid))
                for value in o.values():
                    walk(value)
            elif isinstance(o, list):
                for value in o:
                    walk(value)
        walk(obj)
        if obj is not None:
            continue  # mapping or abstract response is not a full-text body
        name = os.path.basename(path).lower()
        if (re.search(r"full[-_]?text|pmc\d|plain", name)
                or re.search(r"<article\b|<body\b", text)):
            body = inspect(path)
            bodies.append(body)
    # A plaintext derivative is independently corroborated by the JATS body, not its filename.
    xmls = [b for b in bodies if b["xml"] and b["valid"]]
    for body in bodies:
        if not body["xml"] and body["valid"]:
            for source in xmls:
                if (body["claimed_pmcid"] == source["pmcid"]
                        and (not body["claimed_pmid"] or body["claimed_pmid"] == source["pmid"])
                        and compact(source["body"])[:200] in compact(body["body"])):
                    body["pmid"].update(source["pmid"])
                    body["pmcid"].update(source["pmcid"])
            pairs = {(pmid, pmcid) for pmid, pmcid in mappings
                     if body["claimed_pmcid"] == {pmcid}}
            # Contradictory independent mappings are ambiguous, not a menu from
            # which a generated header can choose its preferred source.
            if len(pairs) == 1:
                pmid, pmcid = next(iter(pairs))
                if not body["claimed_pmid"] or body["claimed_pmid"] == {pmid}:
                    body["pmid"].add(pmid)
                    body["pmcid"].add(pmcid)
    return bodies, mappings


def record_ids(ctx):
    records = ctx.get("fixture", {}).get("response", {}).get("result", {}).get("data", [])
    result = {}
    for i, esid in enumerate(ctx.get("check", {}).get("esids", []), 1):
        rec = next((r for r in records if r.get("clinical_result_extra_esid") == esid), {})
        link = str(rec.get("clinical_result_full_article_link") or "")
        pmid = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", link)
        pmcid = re.search(r"\bPMC\d+\b", link)
        result[f"ref_{i}"] = ({pmid.group(1)} if pmid else set(), {pmcid.group()} if pmcid else set())
    return result


def attributed(sv, ctx):
    bodies, mappings = evidence(sv.get("artifacts_dir"), sv.get("run_dir"))
    by_ref, unmapped = {}, []
    for b in bodies:
        refs = []
        if b["valid"]:
            for ref, (pmids, pmcids) in record_ids(ctx).items():
                if pmids & b["pmid"] or pmcids & b["pmcid"]:
                    refs.append(ref)
        if len(refs) == 1:
            by_ref.setdefault(refs[0], []).append(b)
        else:
            unmapped.append(b["name"])
    return by_ref, unmapped
