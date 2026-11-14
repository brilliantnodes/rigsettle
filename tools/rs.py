#!/usr/bin/env python3
"""Small command-line client for RigSettle on GenLayer Studio (studionet).

Test GEN only. Keys passed on the command line or in RS_KEY are throwaway
Studio keys; never use a key that holds anything of value.

  python tools/rs.py deploy                      # deploy contracts/rigsettle.py
  python tools/rs.py show <id>                   # print one agreement
  python tools/rs.py latest                      # list recent agreements
"""
import json
import os
import sys
import time
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet
from genlayer_py.types import TransactionStatus

ROOT = Path(__file__).resolve().parents[1]
def _site_address() -> str:
    """The deployed address the site uses (web/src/config.js)."""
    try:
        text = (ROOT / "web" / "src" / "config.js").read_text()
        return text.split('CONTRACT_ADDRESS = "', 1)[1].split('"', 1)[0]
    except Exception:
        return ""


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


def wait(c, tx, status=TransactionStatus.ACCEPTED, retries=200):
    """Wait for a receipt. Studio's gateway sometimes answers 502 for a few
    seconds; that is retried instead of treated as a failure."""
    deadline = time.time() + retries * 3
    last = None
    while time.time() < deadline:
        try:
            return c.wait_for_transaction_receipt(transaction_hash=tx, status=status, interval=3000, retries=20)
        except Exception as e:  # gateway error or still pending
            last = e
            time.sleep(5)
    raise RuntimeError(f"no receipt for {tx}: {last}")


def receipt_result(r):
    """The method's return value and status from a receipt."""
    lr = (r.get("consensus_data") or {}).get("leader_receipt")
    lr = lr[0] if isinstance(lr, list) and lr else lr
    lr = lr if isinstance(lr, dict) else {}
    res = lr.get("result") or {}
    payload = res.get("payload") if isinstance(res, dict) else None
    if isinstance(payload, dict) and "readable" in payload:
        try:
            payload = json.loads(payload["readable"])
        except Exception:
            payload = payload["readable"]
    return {
        "status": r.get("status_name"),
        "execution": lr.get("execution_result"),
        "result": payload,
        "votes": (r.get("consensus_data") or {}).get("votes"),
    }


def write(c, address, fn, args, value=0, acct=None):
    tx = None
    for attempt in range(3):
        try:
            tx = c.write_contract(address=address, function_name=fn, args=args, value=value, account=acct)
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5)
    r = wait(c, tx)
    return tx, receipt_result(r)


def read(c, address, fn, args=None):
    return c.read_contract(address=address, function_name=fn, args=args or [])


def deploy():
    c, acct = client(os.environ.get("RS_KEY"))
    fund(c, acct.address, 10)
    code = (ROOT / "contracts" / "rigsettle.py").read_text()
    tx = c.deploy_contract(code=code)
    r = wait(c, tx)
    addr = r.get("to_address") or r.get("recipient")
    print(json.dumps({"tx": tx, "address": addr, "status": r.get("status_name")}, indent=2))
    return addr


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "deploy":
        deploy()
        return
    addr = os.environ.get("RS_ADDRESS") or DEFAULT_ADDRESS
    c, _ = client()
    if cmd == "show":
        print(json.dumps(read(c, addr, "get_agreement", [sys.argv[2]]), indent=2, default=str))
    elif cmd == "latest":
        for a in read(c, addr, "get_latest", [20]):
            print(a["id"], a["state"], a["terms"]["pool_name"], a["terms"]["worker_name"], (a.get("result") or {}).get("rule"))


if __name__ == "__main__":
    main()
