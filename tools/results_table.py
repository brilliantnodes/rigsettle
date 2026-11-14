#!/usr/bin/env python3
"""Print the README's live-results table from the chain.

  python tools/results_table.py runs.json     # address from web/src/config.js

runs.json maps agreement ids to how each run was driven, for example
{"1": "command line", "13": "site, Chrome"}. Every other column is read
from the contract, so the table cannot drift from what happened.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rs import DEFAULT_ADDRESS, client, read  # noqa: E402

G = 10**18


def gen(wei) -> str:
    s = f"{int(wei) / G:.4f}".rstrip("0").rstrip(".")
    return s


def case(a) -> str:
    w, st, res = a["terms"]["worker_name"], a["state"], a.get("result") or {}
    ev = a.get("evidence") or {}
    if st == "RELEASED":
        return "Both parties agree a split"
    if st == "CANCELLED":
        return "Buyer cancels before acceptance"
    if st == "EXPIRED":
        return "Never accepted: expired"
    if w == "rig-outage":
        reported = any((ev.get(p) or {}).get("intervals") for p in ("buyer", "seller"))
        return "Pool outage, with outage report" if reported else "Pool outage, no report"
    return {"rig-steady": "Steady rig", "rig-sixty": "Rig delivering about 60%", "rig-gappy": "Rig idles 2 of 5 minutes, pool hides them",
            "rig-ghost": "Seller never shows", "rig-dark": "Pool page goes dark"}.get(w, w)


def main():
    runs = json.loads(open(sys.argv[1]).read()) if len(sys.argv) > 1 else {}
    c, _ = client()
    n = read(c, DEFAULT_ADDRESS, "get_count")
    print("| # | Case | Run through | Measured | Paid share | Rule | Buyer / seller GEN |")
    print("|---|---|---|---|---|---|---|")
    open_ids = []
    for i in range(1, n + 1):
        a = read(c, DEFAULT_ADDRESS, "get_agreement", [str(i)])
        if a["state"] in ("OPEN", "ACTIVE"):
            open_ids.append(i)
            continue
        r = a.get("result") or {}
        raw = r.get("raw_share_bp")
        measured = f"{raw / 100:.2f}%" if raw is not None else "–"
        paid = f"{r['share_bp'] / 100:.2f}%" if r.get("share_bp") is not None else "–"
        print(f"| #{i} | {case(a)} | {runs.get(str(i), '')} | {measured} | {paid} | `{r.get('rule')}` | {gen(r.get('paid_buyer', 0))} / {gen(r.get('paid_seller', 0))} |")
    print(f"\nagreements: {n}; still open: {open_ids}; locked: {read(c, DEFAULT_ADDRESS, 'get_locked')} wei")


if __name__ == "__main__":
    main()
