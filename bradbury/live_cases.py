"""RigSettle live cases on Testnet Bradbury Phase 2 (GenVM v0.6 packed build).

Buyer = deployer key, seller = a second throwaway key (both test GEN only).
Cases (fictional pools, our demo pages): steady, sixty, outage with evidence,
ghost (worker never shows), and an agreed split. Price 2 GEN, bond 1 GEN.
Payouts are external messages that run at finalization; the seller's balance
is compared before and after the settlements finalize to prove they arrived.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS = Path(os.environ.get("GLP_BRADBURY_TOOLS", str(HERE.parents[1] / "genlayer-patterns" / "bradbury" / "tools")))
OUT = HERE / "results" / "live-cases.json"
ADDR = os.environ["RS_ADDR"]
BUYER_KEY = os.environ["BUYER_KEY_FILE"]  # throwaway keys, never committed
SELLER_KEY = os.environ["SELLER_KEY_FILE"]
BUYER = os.environ.get("BUYER_ADDRESS", "0x77F1635B8F2eca3b7Eb46fB2534B7Fa18aCd2734")
SELLER = os.environ.get("SELLER_ADDRESS", "0xF5d92105174434618ae0f0E0C65D50Ae6d57eDb7")
SITE = "https://rigsettle.brilliantnodes.com/demo"
STATUS = f"{SITE}/saltmarsh-status/"
G, GH = 10**18, 10**9
PRICE, BOND = 2 * G, 1 * G
CASES = {
    "steady": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", expect=("SETTLED", "G1_WITHIN_GRACE")),
    "sixty": dict(pool="Fernhollow Pool", worker="rig-sixty", path="fernhollow/rig-sixty", expect=("SETTLED", "S2_PRO_RATA")),
    "outage_evidence": dict(pool="Saltmarsh Pool", worker="rig-outage", path="saltmarsh/rig-outage", evidence=True, expect=("SETTLED", "G1_WITHIN_GRACE")),
    "ghost": dict(pool="Fernhollow Pool", worker="rig-ghost", path="fernhollow/rig-ghost", expect=("SETTLED", "Z1_WORKER_NOT_LISTED")),
    "release": dict(pool="Fernhollow Pool", worker="rig-steady", path="fernhollow/rig-steady", release=7500, expect=("RELEASED", "R1_AGREED_SPLIT")),
}


def node(key, *args):
    env = {**os.environ, "BRADBURY_KEY_FILE": key}
    p = subprocess.run(["node", "gl.mjs", *args], cwd=JS, capture_output=True, text=True, timeout=1800, env=env)
    lines = [l for l in p.stdout.splitlines() if l.startswith("{")]
    return json.loads(lines[-1]) if lines else {"ok": False, "error": p.stderr[-600:]}


def row(d):
    raw = d.get("raw") or {}
    lr = raw.get("lastRound") or {}
    return {"tx": d.get("hash"), "result": raw.get("resultName"), "execution": raw.get("txExecutionResultName"),
            "votes": lr.get("votesRevealed"), "validators": lr.get("validatorsCount"), "error": d.get("error")}


def write(key, fn, args, value=0, payees=()):
    d = node(key, "write", ADDR, fn, json.dumps(args), str(value), ",".join(payees))
    r = row(d)
    print(time.strftime("%H:%M:%S"), fn, args[:1], r, flush=True)
    return r


def read(fn, args=None):
    for i in range(6):
        d = node(BUYER_KEY, "read", ADDR, fn, json.dumps(args or []))
        if d.get("ok"):
            return d["result"]
        time.sleep(6)
    raise RuntimeError(f"read {fn}: {d.get('error')}")


def balance(addr):
    return int(node(BUYER_KEY, "balance", addr)["result"])


def status(tx):
    d = node(BUYER_KEY, "status", tx)
    return (d.get("result") or {}).get("status")


def wait_final(txs, minutes=40):
    end = time.time() + minutes * 60
    pending = [t for t in txs if t]
    while pending and time.time() < end:
        pending = [t for t in pending if status(t) != "FINALIZED"]
        if pending:
            time.sleep(20)
    return not pending


def until(ts):
    while time.time() < ts:
        time.sleep(min(10, max(1, ts - time.time())))


def save(out):
    OUT.write_text(json.dumps(out, indent=2, default=str) + "\n")


def main():
    start = (int(time.time()) // 60 + 26) * 60
    end = start + 5 * 60
    out = {"network": "testnet-bradbury-phase-2", "chain_id": 4221, "address": ADDR, "buyer": BUYER, "seller": SELLER,
           "price_wei": str(PRICE), "bond_wei": str(BOND), "window": [start, end], "cases": {}}
    seller_txs = []
    for name, cfg in CASES.items():
        args = [SELLER, cfg["pool"], cfg["worker"], f"{SITE}/{cfg['path']}/", STATUS, 10 * GH, 1, start, 5, BOND, 300, start, 5, 60]
        before = int(read("get_count"))
        r = write(BUYER_KEY, "create", args, value=PRICE)
        for _ in range(30):
            n = int(read("get_count"))
            if n > before:
                break
            time.sleep(6)
        out["cases"][name] = {"id": str(n), "create": r}
        save(out)
    for name, c in out["cases"].items():
        for attempt in range(3):
            r = write(SELLER_KEY, "probe_meter", [c["id"]])
            seller_txs.append(r["tx"])
            probe = read("get_agreement", [c["id"]]).get("probe")
            if isinstance(probe, dict) and probe.get("ok"):
                break
        c["probe"] = {**r, "probe": probe}
        r = write(SELLER_KEY, "accept", [c["id"]], value=BOND)
        seller_txs.append(r["tx"])
        c["accept"] = r
        c["state_after_accept"] = read("get_agreement", [c["id"]])["state"]
        save(out)
    rel = out["cases"]["release"]
    rel["release_buyer"] = write(BUYER_KEY, "propose_release", [rel["id"], 7500])
    rel["release_seller"] = write(SELLER_KEY, "propose_release", [rel["id"], 7500], payees=(BUYER, SELLER))
    seller_txs.append(rel["release_seller"]["tx"])
    save(out)
    until(end + 20)
    ev = out["cases"]["outage_evidence"]
    ev["evidence"] = write(SELLER_KEY, "add_evidence", [ev["id"], STATUS])
    seller_txs.append(ev["evidence"]["tx"])
    ev["evidence_recorded"] = read("get_agreement", [ev["id"]]).get("evidence")
    save(out)
    print("waiting for the seller's own transactions to finalize", flush=True)
    out["seller_txs_final"] = wait_final(seller_txs)
    out["seller_balance_before_settle"] = str(balance(SELLER))
    until(end + 5 * 60 + 10)
    settle_txs = []
    for name in ("steady", "sixty", "outage_evidence", "ghost"):
        c = out["cases"][name]
        c["settle"] = write(BUYER_KEY, "settle", [c["id"]], payees=(BUYER, SELLER))
        settle_txs.append(c["settle"]["tx"])
        save(out)
    for name, c in out["cases"].items():
        a = read("get_agreement", [c["id"]])
        res = a.get("result") or {}
        c.update({"state": a.get("state"), "rule": res.get("rule"), "share_bp": res.get("share_bp"), "paid_buyer": res.get("paid_buyer"),
                  "paid_seller": res.get("paid_seller"), "excused_slots": res.get("excused_slots"),
                  "ok": (a.get("state"), res.get("rule")) == CASES[name]["expect"]})
        print("result", name, c["state"], c["rule"], c["share_bp"], c["paid_seller"], "ok" if c["ok"] else "MISMATCH", flush=True)
    save(out)
    print("waiting for the settlements to finalize", flush=True)
    out["settle_txs_final"] = wait_final(settle_txs)
    after = balance(SELLER)
    expected = sum(int(out["cases"][n].get("paid_seller") or 0) for n in ("steady", "sixty", "outage_evidence", "ghost"))
    out["seller_balance_after_settle"] = str(after)
    out["seller_received"] = str(after - int(out["seller_balance_before_settle"]))
    out["seller_expected"] = str(expected)
    out["payouts_arrived"] = after - int(out["seller_balance_before_settle"]) == expected
    out["locked_after"] = read("get_locked")
    out["count"] = read("get_count")
    save(out)
    print("done payouts_arrived", out["payouts_arrived"], out["seller_received"], expected, "locked", out["locked_after"], flush=True)


if __name__ == "__main__":
    main()
