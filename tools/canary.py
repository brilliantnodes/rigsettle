#!/usr/bin/env python3
"""Daily canary: run three fictional rentals against the deployed contract
(steady rig, 60% rig, no-show) and fail if any outcome differs from the
expected one. The demo pages follow a fixed formula, so a changed outcome
means the validators' models or the network changed how they read them.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADDRESS = os.environ.get("RS_ADDRESS", "0xE74E206a60DD7e284FF3e0452DB8078a464daa11")
OUT = Path(os.environ.get("RS_OUT", "canary_results.json"))


def main():
    env = {**os.environ, "RS_ADDRESS": ADDRESS, "RS_OUT": str(OUT)}
    subprocess.run([sys.executable, str(HERE / "live_cases.py"), "steady", "sixty", "ghost"], env=env, check=False)
    res = json.loads(OUT.read_text())["results"]
    bad = [k for k, v in res.items() if not v.get("pass")]
    for k, v in res.items():
        print(f"{'ok  ' if v.get('pass') else 'FAIL'} {k:8} state={v.get('state')} rule={v.get('rule')} share={v.get('share_bp')} {v.get('error', '')}")
    sys.exit(1 if bad or len(res) != 3 else 0)


if __name__ == "__main__":
    main()
