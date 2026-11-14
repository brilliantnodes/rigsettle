#!/usr/bin/env python3
"""Run the fictional demo cases live against a deployed RigSettle on Studio.

Every pool, worker and coin here is fictional. Each case uses two fresh
throwaway Studio accounts funded from Studio's built-in faucet. All windows
start at the same aligned minute so the cases run side by side.

  RS_ADDRESS=0x... python tools/live_cases.py [case ...]
"""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rs import G, GH, SITE, client, fund, read, write  # noqa: E402

ADDR = os.environ["RS_ADDRESS"]
OUT = Path(os.environ.get("RS_OUT", "live_results.json"))
LOCK = threading.Lock()
RESULTS = {}

CASES = {
    "steady": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", expect=("SETTLED", "G1_WITHIN_GRACE", 10000)),
    "sixty": dict(pool="Fernhollow Pool", worker="rig-sixty", path="fernhollow/rig-sixty", expect=("SETTLED", "S2_PRO_RATA", (5700, 6300))),
    "outage_evidence": dict(pool="Saltmarsh Pool", worker="rig-outage", path="saltmarsh/rig-outage", evidence=True, expect=("SETTLED", "G1_WITHIN_GRACE", 10000)),
    "outage_no_evidence": dict(pool="Saltmarsh Pool", worker="rig-outage", path="saltmarsh/rig-outage", expect=("SETTLED", "S2_PRO_RATA", (5900, 6100))),
    "ghost": dict(pool="Fernhollow Pool", worker="rig-ghost", path="fernhollow/rig-ghost", expect=("SETTLED", "Z1_WORKER_NOT_LISTED", 0)),
    "dark": dict(pool="Quillmoor Pool", worker="rig-dark", path="quillmoor/rig-dark", dark=True, expect=("SETTLED", "D1_METER_DARK_AFTER_WINDOW", 10000)),
    "release": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", release=7500, expect=("RELEASED", "R1_AGREED_SPLIT", 7500)),
}


def log(name, msg):
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    with LOCK:
        print(f"{stamp} [{name}] {msg}", flush=True)


def until(ts):
    while time.time() < ts:
        time.sleep(min(5, max(0.5, ts - time.time())))


def run(name, cfg, start):
    rec = {"case": name, "txs": {}}
    try:
        cb, buyer = client()
        cs, seller = client()
        fund(cb, buyer.address, 50)
        fund(cs, seller.address, 50)
        time.sleep(3)
        end = start + 5 * 60
        status = f"{SITE}/saltmarsh-status/"
        args = [seller.address, cfg["pool"], cfg["worker"], f"{SITE}/{cfg['path']}/", status, 10 * GH, 1, start, 5, 2 * G, 300, start, 2, 12]
        tx, r = write(cb, ADDR, "create", args, value=10 * G)
        rec["txs"]["create"] = tx
        log(name, f"create {r['status']} {r['result']}")
        aid = r["result"]["id"]
        rec["id"] = aid
        tx, r = write(cs, ADDR, "probe_meter", [aid])
        rec["txs"]["probe"] = tx
        log(name, f"probe {r['status']} {r['result']}")
        tx, r = write(cs, ADDR, "accept", [aid], value=2 * G)
        rec["txs"]["accept"] = tx
        log(name, f"accept {r['status']} {r['result']}")
        if not (isinstance(r["result"], dict) and r["result"].get("ok")):
            raise RuntimeError(f"accept failed: {r}")
        if cfg.get("release"):
            tx, r = write(cb, ADDR, "propose_release", [aid, cfg["release"]])
            rec["txs"]["release_buyer"] = tx
            tx, r = write(cs, ADDR, "propose_release", [aid, cfg["release"]])
            rec["txs"]["release_seller"] = tx
            log(name, f"release {r['status']} {r['result']}")
        else:
            if cfg.get("evidence"):
                until(end + 15)
                tx, r = write(cs, ADDR, "add_evidence", [aid, status])
                rec["txs"]["evidence"] = tx
                log(name, f"evidence {r['status']} {r['result']}")
            until(end + 2 * 60 + 5)
            tx, r = write(cb, ADDR, "settle", [aid])
            rec["txs"]["settle"] = tx
            log(name, f"settle {r['status']} {r['result']} votes={r['votes']}")
            if cfg.get("dark"):
                until(end + 12 * 60 + 10)
                tx, r = write(cs, ADDR, "settle_default", [aid])
                rec["txs"]["settle_default"] = tx
                log(name, f"settle_default {r['status']} {r['result']}")
        a = read(cb, ADDR, "get_agreement", [aid])
        res = a.get("result") or {}
        rec.update(state=a["state"], rule=res.get("rule"), share_bp=res.get("share_bp"), raw_share_bp=res.get("raw_share_bp"),
                   paid_buyer=res.get("paid_buyer"), paid_seller=res.get("paid_seller"), buyer=buyer.address, seller=seller.address)
        want_state, want_rule, want_share = cfg["expect"]
        share = rec["share_bp"]
        share_ok = (want_share[0] <= share <= want_share[1]) if isinstance(want_share, tuple) else share == want_share
        rec["pass"] = a["state"] == want_state and rec["rule"] == want_rule and share_ok
        log(name, f"RESULT {'PASS' if rec['pass'] else 'FAIL'} state={a['state']} rule={rec['rule']} share={share} raw={rec['raw_share_bp']}")
    except Exception as e:
        rec["pass"] = False
        rec["error"] = str(e)[:500]
        log(name, f"ERROR {e}")
    with LOCK:
        RESULTS[name] = rec


def main():
    names = sys.argv[1:] or list(CASES)
    now = time.time()
    # first minute that is a multiple of 10 and at least 9 minutes away
    m = int(now // 60) + 9
    while m % 10:
        m += 1
    start = m * 60
    print("window", datetime.fromtimestamp(start, timezone.utc).isoformat(), "to", datetime.fromtimestamp(start + 300, timezone.utc).isoformat(), flush=True)
    threads = [threading.Thread(target=run, args=(n, CASES[n], start)) for n in names]
    for i, t in enumerate(threads):
        t.start()
        time.sleep(2)
    for t in threads:
        t.join()
    OUT.write_text(json.dumps({"address": ADDR, "window_start": start, "results": RESULTS}, indent=2))
    ok = sum(1 for r in RESULTS.values() if r.get("pass"))
    print(f"\n{ok}/{len(RESULTS)} cases passed")


if __name__ == "__main__":
    main()
