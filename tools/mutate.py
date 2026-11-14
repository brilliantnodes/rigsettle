#!/usr/bin/env python3
"""Mutation check: break the contract on purpose, one change at a time, and
confirm that the direct-mode tests catch every break.

    PYTHONPATH=. python tools/mutate.py

Each mutant is written to a temporary file and the tests are pointed at it
with RS_CONTRACT; contracts/rigsettle.py itself is never modified.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "contracts" / "rigsettle.py").read_text()

MUTANTS = [
    ("tolerance 2 -> 20 points", "SHARE_TOLERANCE_BP = 200", "SHARE_TOLERANCE_BP = 2000"),
    ("grace-edge tolerance 0.5 -> 2 points", "GRACE_EDGE_TOLERANCE_BP = 50", "GRACE_EDGE_TOLERANCE_BP = 200"),
    ("no coverage rule", "MIN_COVERAGE_BP = 5000", "MIN_COVERAGE_BP = 0"),
    ("missing slot paid in full", "measured_by_slot.get(i, 0)", "measured_by_slot.get(i, rate)"),
    ("outage slot not excused", "            delivered += rate\n", "            delivered += measured\n"),
    ("no per-slot cap", "delivered += min(measured, rate)", "delivered += measured"),
    ("grace edge exclusive", 'if raw >= BP - t["grace_bp"]:', 'if raw > BP - t["grace_bp"]:'),
    ("outage excuse without report", "if down and measured < rate:", "if measured < rate:"),
    ("no-show paid", '"share_bp": 0, "metered_slots": 0', '"share_bp": BP, "metered_slots": 0'),
    ("bond split reversed", "bond_to_buyer = bond * (BP - share_bp) // BP", "bond_to_buyer = bond * share_bp // BP"),
    ("price split reversed", "seller_pay = price * share_bp // BP", "seller_pay = price * (BP - share_bp) // BP"),
    ("stale probe accepted", 'now - probe["at"] > PROBE_FRESH_SECS', 'now - probe["at"] > 10**9'),
    ("any bond accepted", 'if int(gl.message.value) != t["bond"]:', 'if int(gl.message.value) < 0:'),
    ("anyone may accept", "if sender.lower() != a.seller.lower():", "if False:"),
    ("accept at window start", 'if now > t["accept_by"] or now >= t["start_at"]:', 'if now > t["accept_by"]:'),
    ("refused value kept", "        self._send(gl.message.sender_address.as_hex, int(gl.message.value))\n", "        pass\n"),
    ("anyone may cancel", 'if gl.message.sender_address.as_hex.lower() != a.buyer.lower():\n            raise gl.vm.UserError("only the buyer can cancel")', 'if False:\n            raise gl.vm.UserError("only the buyer can cancel")'),
    ("expire any time", 'if a.state != "OPEN" or self._now() <= t["accept_by"]:', 'if a.state != "OPEN":'),
    ("settle before the last slot ends", 'if now < end + t["slot_minutes"] * 60:', "if now < end:"),
    ("settle inside the evidence window", 'if now >= end + t["evidence_minutes"] * 60:\n            return True', "if now >= end:\n            return True"),
    ("one waiver opens settlement", 'return ev["buyer"] is not None and ev["seller"] is not None', 'return ev["buyer"] is not None or ev["seller"] is not None'),
    ("default before the cut-off", 'if now < end + t["default_after_minutes"] * 60:', "if now < end:"),
    ("D1 without a dark attempt", 'x["reason"] == "N1_METER_DARK" and x["at"] >= end', 'x["reason"] != "N1_METER_DARK" and x["at"] >= end'),
    ("evidence from any site", 'if not url.startswith(t["status_prefix"]):', "if False:"),
    ("evidence twice", 'if ev[party] is not None:\n            raise gl.vm.UserError("you have already added or waived evidence")\n        url', 'if False:\n            raise gl.vm.UserError("you have already added or waived evidence")\n        url'),
    ("evidence after the window", 'if self._now() >= end + t["evidence_minutes"] * 60:', "if False:"),
    ("website-only outage counts", 'in ("mining", "stratum"):', 'in ("mining", "stratum", "website_only"):'),
    ("evidence agreement ignores times", 'tol = t["slot_minutes"] * 60', "tol = 10**12"),
    ("any pool's page accepted", 'if kind not in ("worker_stats", "worker_not_found") or t["pool_name"].lower() not in on_page:', 'if kind not in ("worker_stats", "worker_not_found"):'),
    ("non-UTC page accepted", 'if not _yes(ans.get("times_utc")):\n        return {"kind": "NO_READING", "reason": "N2_FORMAT"}', 'if False:\n        return {"kind": "NO_READING", "reason": "N2_FORMAT"}'),
    ("conflicting rows accepted", "if idx in seen and seen[idx] != rate:", "if False:"),
    ("misaligned rows accepted", "if (ts - start) % slot != 0:", "if False:"),
    ("unreadable row skipped", 'if rate is None:\n            return {"kind": "NO_READING", "reason": "N2_FORMAT"}', "if rate is None:\n            continue"),
    ("leader rows beyond the window", "if i <= last or i < 0 or i >= slots", "if i <= last or i < 0 or i >= MAX_SLOTS"),
    ("unlisted worker with rows", 'if not r["listed"] and out:', "if False:"),
    ("listed flag not compared", 'if a["listed"] != b["listed"]:\n        return False', 'if False:\n        return False'),
    ("kind not compared", 'if a["kind"] != b["kind"]:\n        return False\n    if a["kind"] == "NO_READING"', 'if False:\n        return False\n    if a["kind"] == "NO_READING"'),
    ("backslash allowed", 'if "\\\\" in url:', "if False:"),
    ("metadata range allowed", "or (a == 169 and b == 254)", ""),
    ("user info allowed", 'if "@" in authority:', "if False:"),
    # Not listed: dropping the explicit IPv6 check is an equivalent mutant,
    # because the label rules below it already refuse every IPv6 literal.
    ("history unbounded", "MAX_HISTORY = 100", "MAX_HISTORY = 10**6"),
    ("locked not released", 'self.locked = u256(int(self.locked) - owed)', "self.locked = u256(int(self.locked))"),
    ("buyer may sell to self", 'if t["seller"].lower() == buyer.lower():', "if False:"),
    ("release on one proposal", 'if rel["buyer"] is not None and rel["buyer"] == rel["seller"]:', 'if rel["buyer"] is not None or rel["seller"] is not None:'),
    ("probe validator agrees blindly", 'return lr["ok"] == mine["ok"] and lr.get("reason") == mine["reason"]', "return True"),
    ("decimal comma read as thousands", 'if not (groups[0].isdigit() and 1 <= len(groups[0]) <= 3 and all(g.isdigit() and len(g) == 3 for g in groups[1:])):\n            return None', "if False:\n            return None"),
]


def main() -> int:
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    caught = 0
    tmp = Path(tempfile.mkdtemp(prefix="rs-mutants-"))
    for i, (name, old, new) in enumerate(MUTANTS, 1):
        n = SRC.count(old)
        if n != 1:
            print(f"SETUP ERROR  {name}: pattern found {n} times")
            return 2
        path = tmp / f"mutant_{i:02d}.py"
        path.write_text(SRC.replace(old, new))
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/direct", "-q", "-x", "-p", "no:cacheprovider"],
                           cwd=ROOT, env={**env, "RS_CONTRACT": str(path)}, capture_output=True, text=True)
        ok = r.returncode != 0
        caught += ok
        print(f"{'caught ' if ok else 'MISSED '} {i:2d} {name}")
    print(f"\n{caught} of {len(MUTANTS)} mutants caught")
    return 0 if caught == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
