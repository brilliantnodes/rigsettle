#!/usr/bin/env python3
"""Run the fictional demo cases live against a deployed RigSettle on Studio.

Every pool, worker and coin here is fictional. Each case uses two fresh
throwaway Studio accounts funded from Studio's built-in faucet. All windows
start at the same aligned minute so the cases run side by side.

  python tools/live_cases.py [case ...]     # address from web/src/config.js, or RS_ADDRESS
"""
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rs import DEFAULT_ADDRESS, G, GH, SITE, client, fund, read, write  # noqa: E402

ADDR = DEFAULT_ADDRESS
OUT = Path(os.environ.get("RS_OUT", "live_results.json"))
LOCK = threading.Lock()
RESULTS = {}

CASES = {
    "steady": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", expect=("SETTLED", "G1_WITHIN_GRACE", 10000)),
    "sixty": dict(pool="Fernhollow Pool", worker="rig-sixty", path="fernhollow/rig-sixty", expect=("SETTLED", "S2_PRO_RATA", (5700, 6300))),
    "outage_evidence": dict(pool="Saltmarsh Pool", worker="rig-outage", path="saltmarsh/rig-outage", evidence=True, expect=("SETTLED", "G1_WITHIN_GRACE", 10000)),
    "outage_no_evidence": dict(pool="Saltmarsh Pool", worker="rig-outage", path="saltmarsh/rig-outage", expect=("SETTLED", "S2_PRO_RATA", (5900, 6100))),
    "ghost": dict(pool="Fernhollow Pool", worker="rig-ghost", path="fernhollow/rig-ghost", expect=("SETTLED", "Z1_WORKER_NOT_LISTED", 0)),
    # The pool leaves idle minutes out: they count as zero (rule M1), not as an average.
    "gappy": dict(pool="Fernhollow Pool", worker="rig-gappy", path="fernhollow/rig-gappy", expect=("SETTLED", "S2_PRO_RATA", (5800, 6100))),
    "cancel": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", flow="cancel", expect=("CANCELLED", "CANCELLED_BY_BUYER", None)),
    "expire": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", flow="expire", expect=("EXPIRED", "EXPIRED_UNACCEPTED", None)),
    # Refused payable calls send the value straight back: a bad URL at create, a wrong bond at accept.
    "refund": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", flow="refund", expect=("CANCELLED", "CANCELLED_BY_BUYER", None)),
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
        if cfg.get("flow") == "refund":
            bad = list(args)
            bad[3] = "http://[::ffff:169.254.169.254]/latest/meta-data/"
            tx, r = write(cb, ADDR, "create", bad, value=10 * G)
            rec["txs"]["create_refused"] = tx
            rec["create_refused"] = r["result"]
            log(name, f"create with a metadata URL {r['status']} {r['result']}")
            if not (isinstance(r["result"], dict) and r["result"].get("ok") is False and r["result"].get("refunded") == str(10 * G)):
                raise RuntimeError(f"bad URL was not refused and refunded: {r}")
        tx, r = write(cb, ADDR, "create", args, value=10 * G)
        rec["txs"]["create"] = tx
        log(name, f"create {r['status']} {r['result']}")
        aid = r["result"]["id"]
        rec["id"] = aid
        if cfg.get("flow") == "cancel":
            tx, r = write(cb, ADDR, "cancel", [aid])
            rec["txs"]["cancel"] = tx
            log(name, f"cancel {r['status']} {r['result']}")
        elif cfg.get("flow") == "expire":
            until(start + 10)
            tx, r = write(cs, ADDR, "expire", [aid])
            rec["txs"]["expire"] = tx
            log(name, f"expire {r['status']} {r['result']}")
        if cfg.get("flow") in ("cancel", "expire"):
            return finish(name, cfg, rec, cb, aid, buyer, seller)
        for attempt in range(3):
            if cfg.get("dark"):
                # The fictional dark page reads fine only 0-5 minutes past every ten.
                while (int(time.time() // 60) % 10) >= 5:
                    time.sleep(5)
            tx, r = write(cs, ADDR, "probe_meter", [aid])
            rec["txs"]["probe"] = tx
            log(name, f"probe {r['status']} {r['result']}")
            if isinstance(r["result"], dict) and r["result"].get("ok"):
                break
        if cfg.get("flow") == "refund":
            tx, r = write(cs, ADDR, "accept", [aid], value=1 * G)
            rec["txs"]["accept_refused"] = tx
            rec["accept_refused"] = r["result"]
            log(name, f"accept with the wrong bond {r['status']} {r['result']}")
            if not (isinstance(r["result"], dict) and r["result"].get("ok") is False and r["result"].get("refunded") == str(1 * G)):
                raise RuntimeError(f"wrong bond was not refused and refunded: {r}")
            tx, r = write(cb, ADDR, "cancel", [aid])
            rec["txs"]["cancel"] = tx
            log(name, f"cancel {r['status']} {r['result']}")
            return finish(name, cfg, rec, cb, aid, buyer, seller)
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
        finish(name, cfg, rec, cb, aid, buyer, seller)
    except Exception as e:
        rec["pass"] = False
        rec["error"] = str(e)[:500]
        log(name, f"ERROR {e}")
        with LOCK:
            RESULTS[name] = rec


def finish(name, cfg, rec, cb, aid, buyer, seller):
    """Read the agreement back (Studio may briefly answer with the previous
    state, so retry until it is closed) and compare with the expectation."""
    a = None
    for _ in range(10):
        a = read(cb, ADDR, "get_agreement", [aid])
        if a["state"] not in ("OPEN", "ACTIVE"):
            break
        time.sleep(3)
    res = a.get("result") or {}
    rec.update(state=a["state"], rule=res.get("rule"), share_bp=res.get("share_bp"), raw_share_bp=res.get("raw_share_bp"),
               missing_slots=res.get("missing_slots"), paid_buyer=res.get("paid_buyer"), paid_seller=res.get("paid_seller"),
               buyer=buyer.address, seller=seller.address)
    want_state, want_rule, want_share = cfg["expect"]
    share = rec["share_bp"]
    if isinstance(want_share, tuple):
        share_ok = share is not None and want_share[0] <= share <= want_share[1]
    else:
        share_ok = share == want_share
    rec["pass"] = a["state"] == want_state and rec["rule"] == want_rule and share_ok
    log(name, f"RESULT {'PASS' if rec['pass'] else 'FAIL'} state={a['state']} rule={rec['rule']} share={share} raw={rec['raw_share_bp']}")
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
