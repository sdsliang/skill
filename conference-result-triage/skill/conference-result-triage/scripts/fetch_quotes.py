#!/usr/bin/env python3
"""Attach a verifiable meeting-window price move to every listed sponsor (off-platform).

    python3 fetch_quotes.py --cards output/watchlist.json --meeting-start 2026-10-17 \
        --out work/quotes.json --evidence work/web/quotes.jsonl

Why this is a *local* helper and not a platform step: the sandbox runs with
``sandbox_internet=false``, so it cannot reach a quote API. On the platform the same
numbers come from ``web_fetch`` reading the same JSON endpoint (see SKILL.md Step 5B);
this script exists so a reviewer can precompute the block once and hand it to
``make_cards.py --quotes``.

The move is deliberately *not* attributed to the readout: it is the sponsor's first
trading session inside the meeting window against the last close before it. Anything
stronger ("jumped on the abstract") would be a causal claim the data cannot carry.
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

# Eastmoney market ids. Everything absent here is unsupported on purpose -- a wrong
# market id silently returns another company's series, which is worse than a blank.
MARKETS = {"NASDAQ": 105, "NYSE": 106, "AMEX": 107, "HKEX": 116, "LSE": 155}
KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def secid(ticker: str, exchange: str) -> Optional[str]:
    market = MARKETS.get((exchange or "").strip().upper())
    if not market or not ticker:
        return None
    code = ticker.strip().upper()
    if market == 116:  # HKEX quotes want the 5-digit form: 1093 -> 01093
        code = code.lstrip("0").zfill(5)
    return f"{market}.{code}"


def kline_url(sid: str, start: date, end: date) -> str:
    query = urllib.parse.urlencode({
        "secid": sid, "fields1": "f1,f2", "fields2": "f51,f53",
        "klt": "101", "fqt": "1",
        "beg": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
    })
    return f"{KLINE}?{query}"


def closes(sid: str, start: date, end: date, timeout: float = 20.0,
           attempts: int = 3) -> Dict[str, float]:
    # Eastmoney drops connections when hit back-to-back; a dropped socket is a
    # transient condition (retry), not an unsupported market (skip).
    payload: Dict[str, Any] = {}
    for attempt in range(attempts):
        request = urllib.request.Request(kline_url(sid, start, end), headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    data = payload.get("data") or {}
    series: Dict[str, float] = {}
    for line in data.get("klines") or []:
        day, close = line.split(",")[:2]
        series[day] = float(close)
    return series


def window_move(series: Dict[str, float], meeting_start: date):
    """First session inside the meeting window vs the last close before it."""
    days = sorted(series)
    before = [d for d in days if d < meeting_start.isoformat()]
    inside = [d for d in days if d >= meeting_start.isoformat()]
    if not before or not inside:
        return None
    from_date, to_date = before[-1], inside[0]
    prev_close, close = series[from_date], series[to_date]
    if not prev_close:
        return None
    return {
        "from_date": from_date,
        "to_date": to_date,
        "prev_close": round(prev_close, 4),
        "close": round(close, 4),
        "change_pct": round((close / prev_close - 1) * 100, 2),
        "basis": "meeting-window first session vs prior close (not attributed)",
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cards", help="output/watchlist.json (or any json with cards[])")
    ap.add_argument("--meeting-start", required=True, help="YYYY-MM-DD, first day of the meeting")
    ap.add_argument("--out", default="work/quotes.json")
    ap.add_argument("--evidence", default="work/web/quotes.jsonl")
    ap.add_argument("--pad-days", type=int, default=14)
    ap.add_argument("--timeout", type=float, default=20.0)
    args = ap.parse_args(argv)

    if not args.cards:
        raise SystemExit("--cards is required (esid -> listed_company mapping)")
    try:
        start = date.fromisoformat(args.meeting_start)
    except ValueError:
        raise SystemExit("--meeting-start must be YYYY-MM-DD")

    payload = json.load(open(args.cards, encoding="utf-8"))
    cards = payload.get("cards") or []

    quotes: Dict[str, Dict[str, Any]] = {}
    evidence: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for card in cards:
        esid = str(card.get("esid") or "")
        company = card.get("listed_company")
        if not esid or not isinstance(company, dict):
            continue
        ticker = str(company.get("ticker") or "")
        exchange = str(company.get("exchange") or "")
        sid = secid(ticker, exchange)
        if not sid:
            skipped.append(f"{ticker or '?'}/{exchange or '?':<7} unsupported market")
            continue
        try:
            series = closes(sid, start - timedelta(days=args.pad_days),
                            start + timedelta(days=7), timeout=args.timeout)
        except Exception as exc:  # network hiccup is a skip, never a hard stop
            skipped.append(f"{ticker}/{exchange} fetch failed: {exc.__class__.__name__}")
            continue
        move = window_move(series, start)
        if not move:
            skipped.append(f"{ticker}/{exchange} no session around {start}")
            continue
        move["source_url"] = kline_url(sid, start - timedelta(days=args.pad_days),
                                       start + timedelta(days=7))
        quotes[esid] = {"reaction": move}
        evidence.append({"ticker": ticker, "exchange": exchange,
                         "secid": sid, **{k: move[k] for k in
                                          ("from_date", "to_date", "prev_close",
                                           "close", "change_pct")},
                         "url": move["source_url"]})

    for path in (args.out, args.evidence):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    json.dump({"quotes": quotes}, open(args.out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open(args.evidence, "w", encoding="utf-8") as fh:
        for row in evidence:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"quotes={len(quotes)} evidence={len(evidence)} skipped={len(skipped)}")
    for line in skipped:
        sys.stderr.write(f"  - {line}\n")
    print(f"  -> {args.out}\n  -> {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
