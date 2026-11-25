#!/usr/bin/env python3
"""Small command-line client for RigSettle on GenLayer Studio (studionet).

Test GEN only. Keys passed on the command line or in RS_KEY are throwaway
Studio keys; never use a key that holds anything of value.

  python tools/rs.py deploy                      # deploy contracts/rigsettle.py
  python tools/rs.py show <id>                   # print one agreement
  python tools/rs.py latest                      # list recent agreements

A real rental from the command line (RS_KEY = the caller's key):

  python tools/rs.py create terms.json           # buyer: lock the price
  python tools/rs.py probe <id>                  # anyone: validators check the meter
  python tools/rs.py accept <id>                 # seller: lock the bond
  python tools/rs.py evidence <id> <url>         # buyer or seller: one outage report
  python tools/rs.py waive <id>                  # buyer or seller: no outage report
  python tools/rs.py settle <id>                 # anyone, once settlement opens
  python tools/rs.py default <id>                # anyone, after the cut-off

terms.json holds the frozen terms; see examples/terms-hourly.example.json.
Times are UTC ISO strings, amounts are GEN, the hashrate is GH/s.
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.abi import calldata
from genlayer_py.chains import studionet

# genlayer-py 0.19 removed TransactionStatus and the receipt's status_name; the transaction is read
# from Studio's RPC instead, which still carries "status" and the leader's receipt.
DONE = ("ACCEPTED", "FINALIZED")
FAILED = ("UNDETERMINED", "CANCELED", "LEADER_TIMEOUT", "VALIDATORS_TIMEOUT")

ROOT = Path(__file__).resolve().parents[1]
def _site_address() -> str:
    """The Studio contract the site uses (the "studio" entry of NETWORKS in
    web/src/config.js). Fails loudly rather than returning an empty address."""
    import re
    text = (ROOT / "web" / "src" / "config.js").read_text()
    m = re.search(r'studio:\s*\{[^}]*?contract:\s*"(0x[0-9a-fA-F]{40})"', text, re.S)
    if not m:
        raise SystemExit("could not find the Studio contract address in web/src/config.js")
    return m.group(1)


DEFAULT_ADDRESS = os.environ.get("RS_ADDRESS") or _site_address()
G = 10**18
GH = 10**9
SITE = "https://rigsettle.brilliantnodes.com/demo"


def client(key=None):
    acct = create_account(key) if key else create_account()
    return create_client(chain=studionet, account=acct), acct


def fund(c, address, gen=100):
    """Studio's built-in faucet (sim_fundAccount)."""
    return c.provider.make_request(method="sim_fundAccount", params=[address, gen * G])


def wait(c, tx, retries=200):
    """Wait until the transaction is accepted or has failed, reading it from the RPC.
    Studio's gateway sometimes answers 502 for a few seconds; that is retried
    instead of treated as a failure."""
    deadline = time.time() + retries * 3
    last = None
    while time.time() < deadline:
        try:
            r = c.provider.make_request(method="eth_getTransactionByHash", params=[tx])
            r = r.get("result", r) if isinstance(r, dict) else r
            if isinstance(r, dict) and r.get("status") in DONE + FAILED:
                return r
            last = (r or {}).get("status") if isinstance(r, dict) else r
        except Exception as e:  # gateway error
            last = e
        time.sleep(4)
    raise RuntimeError(f"no receipt for {tx}: {last}")


def receipt_result(r):
    """The method's return value and status from a receipt."""
    lr = (r.get("consensus_data") or {}).get("leader_receipt")
    lr = lr[0] if isinstance(lr, list) and lr else lr
    lr = lr if isinstance(lr, dict) else {}
    res = lr.get("result") or {}
    payload = res.get("payload") if isinstance(res, dict) else res
    if isinstance(payload, dict) and "readable" in payload:
        try:
            payload = json.loads(payload["readable"])
        except Exception:
            payload = payload["readable"]
    elif isinstance(payload, str):  # the raw RPC gives the result base64-encoded
        try:
            raw = base64.b64decode(payload)
            payload = calldata.decode(raw[1:]) if raw[:1] == b"\x00" else raw[1:].decode("utf-8", "replace")
        except Exception:
            pass
    return {
        "status": r.get("status") or r.get("status_name"),
        "execution": lr.get("execution_result"),
        "result": payload,
        "votes": (r.get("consensus_data") or {}).get("votes"),
    }


def write(c, address, fn, args, value=0, acct=None):
    tx = None
    for attempt in range(3):
        try:
            # Studio refuses transactions without a fee distribution since late Nov 2026 (genlayer-py >= 0.19).
            tx = c.write_contract(address=address, function_name=fn, args=args, value=value, account=acct, fees=c.estimate_transaction_fees())
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    r = wait(c, tx)
    return tx, receipt_result(r)


def read(c, address, fn, args=None, tries=8):
    """A view call. Studio's gateway sometimes answers with a 503 page or an internal database error for
    a minute or two; a read changes nothing, so it is simply asked again."""
    for attempt in range(tries):
        try:
            return c.read_contract(address=address, function_name=fn, args=args or [])
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(15)


def deploy():
    c, acct = client(os.environ.get("RS_KEY"))
    fund(c, acct.address, 10)
    code = (ROOT / "contracts" / "rigsettle.py").read_text()
    tx = c.deploy_contract(code=code, fees=c.estimate_transaction_fees())
    r = wait(c, tx)
    addr = r.get("to_address") or r.get("recipient")
    addr = addr or (r.get("data") or {}).get("contract_address")
    print(json.dumps({"tx": tx, "address": addr, "status": r.get("status") or r.get("status_name")}, indent=2))
    return addr


def _ts(text: str) -> int:
    from datetime import datetime
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def _wei(gen) -> int:
    from decimal import Decimal
    return int(Decimal(str(gen)) * G)


def create_args(terms: dict) -> tuple:
    """Terms file to the create() arguments and the price in wei."""
    start = _ts(terms["start_utc"])
    args = [
        terms["seller"], terms["pool_name"], terms["worker_name"], terms["meter_url"], terms.get("status_prefix", ""),
        int(round(float(terms["rate_ghs"]) * GH)), int(terms["slot_minutes"]), start, int(terms["slots"]),
        _wei(terms["bond_gen"]), int(round(float(terms.get("grace_percent", 3)) * 100)),
        _ts(terms.get("accept_by_utc", terms["start_utc"])), int(terms.get("evidence_minutes", 120)),
        int(terms.get("default_after_minutes", 2880)),
    ]
    return args, _wei(terms["price_gen"])


def act(addr: str, cmd: str, rest: list) -> None:
    key = os.environ.get("RS_KEY")
    if not key:
        raise SystemExit("set RS_KEY to the key of the account that acts (a throwaway Studio key)")
    c, acct = client(key)
    if cmd == "create":
        args, price = create_args(json.loads(Path(rest[0]).read_text()))
        tx, r = write(c, addr, "create", args, value=price)
    elif cmd == "accept":
        bond = int(read(c, addr, "get_agreement", [rest[0]])["terms"]["bond"])
        tx, r = write(c, addr, "accept", [rest[0]], value=bond)
    else:
        fn, args = {
            "probe": ("probe_meter", rest[:1]), "settle": ("settle", rest[:1]), "default": ("settle_default", rest[:1]),
            "waive": ("waive_evidence", rest[:1]), "evidence": ("add_evidence", rest[:2]), "cancel": ("cancel", rest[:1]),
            "expire": ("expire", rest[:1]),
        }[cmd]
        tx, r = write(c, addr, fn, args)
    print(json.dumps({"tx": tx, "status": r["status"], "result": r["result"]}, indent=2, default=str))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "deploy":
        deploy()
        return
    addr = os.environ.get("RS_ADDRESS") or DEFAULT_ADDRESS
    if cmd in ("create", "probe", "accept", "evidence", "waive", "settle", "default", "cancel", "expire"):
        act(addr, cmd, sys.argv[2:])
        return
    c, _ = client()
    if cmd == "show":
        print(json.dumps(read(c, addr, "get_agreement", [sys.argv[2]]), indent=2, default=str))
    elif cmd == "latest":
        for a in read(c, addr, "get_latest", [20]):
            print(a["id"], a["state"], a["terms"]["pool_name"], a["terms"]["worker_name"], (a.get("result") or {}).get("rule"))


if __name__ == "__main__":
    main()
