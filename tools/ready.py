#!/usr/bin/env python3
"""Keep one fictional rental ready to settle, so a visitor can watch the
validators settle it in a few minutes instead of waiting for a new window.

Runs every hour from .github/workflows/ready.yml:

  1. Tidy up: any agreement still ACTIVE whose settlement has been open for
     70 minutes, or whose default cut-off has passed, is settled from the
     pool page (anyone may call settle); only if the page gives no reading
     after the cut-off is the default rule applied. Any unaccepted agreement
     past its acceptance deadline is expired. Nobody's money stays locked.
  2. Create a new "rig delivering about 60%" rental between two fresh
     throwaway Studio accounts, probe the meter, accept, and waive outage
     reports on both sides, so settlement opens about 10 minutes later and
     stays open until someone settles it.

Fictional pool, test GEN only.

  python tools/ready.py            # address from web/src/config.js, or RS_ADDRESS
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rs import DEFAULT_ADDRESS, G, GH, SITE, client, fund, read, write  # noqa: E402

ADDR = DEFAULT_ADDRESS
STALE_AFTER = 70 * 60  # so the previous ready rental stays open while the next one matures
LEAD = 4 * 60  # time for the probe and the acceptance before the window


def settle_opens(a):
    t = a["terms"]
    end = t["start_at"] + t["slots"] * t["slot_minutes"] * 60
    ev = a.get("evidence") or {}
    after_slot = end + t["slot_minutes"] * 60
    if ev.get("buyer") and ev.get("seller"):
        return end, after_slot, end + t["default_after_minutes"] * 60
    return end, max(after_slot, end + t["evidence_minutes"] * 60), end + t["default_after_minutes"] * 60


def tidy(c):
    now = time.time()
    for a in read(c, ADDR, "get_latest", [50]):
        _, opens, cutoff = settle_opens(a)
        aid = a["id"]
        try:
            if a["state"] == "OPEN" and now > a["terms"]["accept_by"]:
                tx, r = write(c, ADDR, "expire", [aid])
                print(f"#{aid} expired: {r['status']}")
            elif a["state"] == "ACTIVE" and (now >= cutoff or now >= opens + STALE_AFTER):
                # A real reading first; the default rule only if the page gives none.
                tx, r = write(c, ADDR, "settle", [aid])
                print(f"#{aid} settled by the hourly job: {r['status']} {r['result']}")
                res = r["result"] if isinstance(r["result"], dict) else {}
                if not res.get("settled") and now >= cutoff:
                    tx, r = write(c, ADDR, "settle_default", [aid])
                    print(f"#{aid} default rule: {r['status']} {r['result']}")
        except Exception as e:  # one stuck agreement must not stop the rest
            print(f"#{aid} not tidied: {str(e)[:200]}")


def create_ready():
    cb, buyer = client()
    cs, seller = client()
    fund(cb, buyer.address, 20)
    fund(cs, seller.address, 20)
    time.sleep(3)
    start = (int(time.time() + LEAD) // 60 + 1) * 60
    args = [seller.address, "Fernhollow Pool", "rig-sixty", f"{SITE}/fernhollow/rig-sixty/", f"{SITE}/saltmarsh-status/",
            10 * GH, 1, start, 5, 2 * G, 300, start, 2, 180]
    tx, r = write(cb, ADDR, "create", args, value=10 * G)
    aid = r["result"]["id"]
    print(f"#{aid} created: {tx}")
    tx, r = write(cs, ADDR, "probe_meter", [aid])
    print(f"#{aid} probe: {r['result']}")
    tx, r = write(cs, ADDR, "accept", [aid], value=2 * G)
    print(f"#{aid} accept: {r['result']}")
    if not (isinstance(r["result"], dict) and r["result"].get("ok")):
        raise SystemExit(f"accept failed: {r}")
    write(cb, ADDR, "waive_evidence", [aid])
    write(cs, ADDR, "waive_evidence", [aid])
    print(json.dumps({"ready_id": aid, "window_start": start, "settle_opens": start + 6 * 60}))


def main():
    c, acct = client()
    fund(c, acct.address, 5)
    time.sleep(3)
    tidy(c)
    create_ready()


if __name__ == "__main__":
    main()
