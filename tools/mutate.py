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
    ("outcome not compared", 'return (sa["rule"], sa["share_bp"]) == (sb["rule"], sb["share_bp"])', "return True"),
    ("only the rule compared", 'return (sa["rule"], sa["share_bp"]) == (sb["rule"], sb["share_bp"])', 'return sa["rule"] == sb["rule"]'),
    ("shares within 2 points", 'return (sa["rule"], sa["share_bp"]) == (sb["rule"], sb["share_bp"])', 'return abs(sa["raw_share_bp"] - sb["raw_share_bp"]) <= 200'),
    ("validator ignores outages on record", "sa, sb = _share(t, a, outages), _share(t, b, outages)", "sa, sb = _share(t, a, []), _share(t, b, [])"),
    ("dark reading forgotten after 20 attempts", "if int(a.dark_at) > 0:", 'if any(x["reason"] == "N1_METER_DARK" for x in json.loads(a.attempts_json)):'),
    ("dark flag never set", "                a.dark_at = u256(now)", "                pass"),
    ("coverage guard missing on stored reading", 'if r["listed"] and len(out) * BP < MIN_COVERAGE_BP * slots:\n        raise ValueError("coverage below the minimum")', 'if False:\n        raise ValueError("coverage below the minimum")'),
    ("cut-off ignores the slot length", 'lo = max(t["evidence_minutes"], t["slot_minutes"]) + MIN_DEFAULT_GAP_MINUTES', 'lo = t["evidence_minutes"] + MIN_DEFAULT_GAP_MINUTES'),
    ("settle after the default cut-off", 'if now >= _window(t)[1] + t["default_after_minutes"] * 60:\n            raise', 'if False:\n            raise'),
    ("bare zero is a format error", 'if num == 0 and u == "":\n        return 0', 'if False:\n        return 0'),
    ("outage report before the window ends", 'if self._now() < end:\n            raise gl.vm.UserError("outage reports open', 'if False:\n            raise gl.vm.UserError("outage reports open'),
    ("no digit cap", "    if len(s) > 60:\n        return None\n    exp = 0", "    exp = 0"),
    ("float conversion back", "return num * mult // 10**scale", "return int(num / 10**scale * mult)"),
    ("comma after the dot read", 'if "," in frac or not (', "if not ("),
    ("exponent ignored", "scale = len(frac) - exp", "scale = len(frac)"),
    ("huge rates read", "if num > 10**24 * 10**scale:", "if False:"),
    ("evidence slots not compared", 'return _down_slots(t, a["intervals"]) == _down_slots(t, b["intervals"])', "return True"),
    ("evidence within a slot", 'return _down_slots(t, a["intervals"]) == _down_slots(t, b["intervals"])', 'return len(a["intervals"]) == len(b["intervals"]) and all(abs(x[0] - y[0]) <= 60 * t["slot_minutes"] and abs(x[1] - y[1]) <= 60 * t["slot_minutes"] for x, y in zip(a["intervals"], b["intervals"]))'),
    ("outage overlap off by one slot", "if any(a < start + (i + 1) * slot and b > start + i * slot for a, b in outages)", "if any(a <= start + (i + 1) * slot and b > start + i * slot for a, b in outages)"),
    ("no coverage rule", "MIN_COVERAGE_BP = 5000", "MIN_COVERAGE_BP = 0"),
    ("missing slot paid in full", "measured_by_slot.get(i, 0)", "measured_by_slot.get(i, rate)"),
    ("outage slot not excused", "            delivered += rate\n", "            delivered += measured\n"),
    ("no per-slot cap", "delivered += min(measured, rate)", "delivered += measured"),
    ("grace edge exclusive", 'if raw >= BP - t["grace_bp"]:', 'if raw > BP - t["grace_bp"]:'),
    ("outage excuse without report", "if i in down_slots and measured < rate:", "if measured < rate:"),
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
    ("D1 flag set by any no-reading", 'if reading["reason"] == "N1_METER_DARK" and int(a.dark_at) == 0', 'if int(a.dark_at) == 0'),
    ("D1 flag overwritten by a later dark reading", 'and int(a.dark_at) == 0 and now >= _window(t)[1]:', 'and now >= _window(t)[1]:'),
    ("evidence from any site", 'if not url.startswith(t["status_prefix"]):', "if False:"),
    ("evidence twice", 'if ev[party] is not None:\n            raise gl.vm.UserError("you have already added or waived evidence")\n        url', 'if False:\n            raise gl.vm.UserError("you have already added or waived evidence")\n        url'),
    ("evidence after the window", 'if self._now() >= end + t["evidence_minutes"] * 60:', "if False:"),
    ("website-only outage counts", 'in ("mining", "stratum"):', 'in ("mining", "stratum", "website_only"):'),
    ("evidence agreement ignores kind", 'if a["kind"] != b["kind"]:\n        return False\n    return _down_slots', 'if False:\n        return False\n    return _down_slots'),
    ("any pool's page accepted", 'if kind not in ("worker_stats", "worker_not_found") or t["pool_name"].lower() not in on_page:', 'if kind not in ("worker_stats", "worker_not_found"):'),
    ("non-UTC page accepted", 'if not _yes(ans.get("times_utc")):\n        return {"kind": "NO_READING", "reason": "N2_FORMAT"}', 'if False:\n        return {"kind": "NO_READING", "reason": "N2_FORMAT"}'),
    ("conflicting rows accepted", "if idx in seen and seen[idx] != rate:", "if False:"),
    ("misaligned rows accepted", "if (ts - start) % slot != 0:", "if False:"),
    ("unreadable row skipped", 'if rate is None:\n            return {"kind": "NO_READING", "reason": "N2_FORMAT"}', "if rate is None:\n            continue"),
    ("leader rows beyond the window", "if i <= last or i < 0 or i >= slots", "if i <= last or i < 0 or i >= MAX_SLOTS"),
    ("unlisted worker with rows", 'if not r["listed"] and out:', "if False:"),
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
    ("decimal comma read as thousands", 'if "," in frac or not (groups[0] != "" and all(c in DIGITS for c in groups[0]) and len(groups[0]) <= 3 and all(len(g) == 3 and all(c in DIGITS for c in g) for g in groups[1:])):\n            return None', 'if "," in frac:\n            return None'),
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
