#!/usr/bin/env python3
"""End-to-end test of the RigSettle site against the live contract on Studio.

Plays both parties in one browser: two temporary accounts, a fictional
example, create -> probe -> accept -> (outage report or waivers) -> settle,
then checks the result card. Also checks that the page never scrolls
sideways. Every pool here is fictional; Studio's faucet pays for everything.

  python tests/e2e/site_flow.py <browser> <device> <preset> [site_url]

  browser: chromium | firefox | webkit
  device:  desktop | "iPhone 15" | "Pixel 7" (Playwright device names)
  preset:  steady | sixty | gappy | outage | ghost

Optional: HTTPS_PROXY (sent to the browser), FIREFOX_PROFILE (a profile dir
that trusts the proxy's CA), E2E_OUT (JSON result file).
"""
import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

BROWSER, DEVICE, PRESET = sys.argv[1], sys.argv[2], sys.argv[3]
URL = sys.argv[4] if len(sys.argv) > 4 else "https://rigsettle.brilliantnodes.com/"
OUT = os.environ.get("E2E_OUT", f"e2e_{BROWSER}_{DEVICE.replace(' ', '_')}_{PRESET}.json")
EXPECT = {"steady": (9700, 10000), "sixty": (5700, 6300), "gappy": (5800, 6100), "outage": (9700, 10000), "ghost": (0, 0)}


def log(msg):
    print(time.strftime("%H:%M:%S"), f"[{BROWSER}/{DEVICE}/{PRESET}]", msg, flush=True)


def no_sideways(page):
    return page.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth + 1")


def click_when(page, name, timeout_s):
    btn = page.get_by_role("button", name=name)
    btn.first.wait_for(state="visible", timeout=timeout_s * 1000)
    page.wait_for_function("b => !b.disabled", arg=btn.first.element_handle(), timeout=timeout_s * 1000)
    btn.first.click()


def wait_tx(page, timeout_s=480):
    """Wait until the transaction card shows a final note."""
    page.wait_for_function(
        """() => { const n = document.getElementById('life-note'); const t = n ? n.textContent : '';
                  return /Accepted by a majority|refused|did not agree|did not answer|not sent|Not settled/.test(t); }""",
        timeout=timeout_s * 1000)
    return page.locator("#life-note").text_content()


def main():
    res = {"browser": BROWSER, "device": DEVICE, "preset": PRESET, "url": URL, "steps": []}
    with sync_playwright() as p:
        bt = getattr(p, BROWSER)
        proxy = {"server": os.environ["HTTPS_PROXY"], "bypass": "127.0.0.1,localhost"} if os.environ.get("HTTPS_PROXY") else None
        ctx_args = dict(p.devices[DEVICE]) if DEVICE != "desktop" else {"viewport": {"width": 1280, "height": 900}}
        if BROWSER == "firefox":
            ctx_args.pop("is_mobile", None)
        if BROWSER == "firefox" and os.environ.get("FIREFOX_PROFILE"):
            ctx = bt.launch_persistent_context(os.environ["FIREFOX_PROFILE"], headless=True, proxy=proxy, **ctx_args)
        else:
            browser = bt.launch(headless=True, proxy=proxy)
            ctx = browser.new_context(**ctx_args)
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.locator("#recent button").first.wait_for(timeout=90000)
        res["steps"].append(("loaded", no_sideways(page)))
        click_when(page, "Play both parties", 30)
        page.wait_for_function("() => /Balance: \\d/.test(document.getElementById('seller-bal').textContent)", timeout=90000)
        log("accounts funded")
        page.get_by_role("button", name={"steady": "Steady rig", "sixty": "Rig delivering 60%", "gappy": "Pool hides idle minutes",
                                         "outage": "Pool outage", "ghost": "Seller never shows"}[PRESET]).click()
        click_when(page, "Lock the price and create", 10)
        log("create: " + wait_tx(page, 300))
        page.locator("#ag-view .badge.OPEN").wait_for(timeout=120000)
        aid = page.locator("#ag-id").input_value()
        res["id"] = aid
        log(f"agreement #{aid} OPEN")
        click_when(page, "Check the meter", 60)
        log("probe: " + wait_tx(page))
        click_when(page, "Accept and lock", 120)
        log("accept: " + wait_tx(page, 300))
        page.locator("#ag-view .badge.ACTIVE").wait_for(timeout=120000)
        res["steps"].append(("active", no_sideways(page)))
        if PRESET == "outage":
            click_when(page, "Add outage report (seller)", 1200)  # offered once the window has ended
            log("evidence: " + wait_tx(page))
            click_when(page, "Waive", 120)
            log("buyer waives: " + wait_tx(page))
        else:
            click_when(page, "Waive", 900)
            log("waive 1: " + wait_tx(page))
            click_when(page, "Waive", 120)
            log("waive 2: " + wait_tx(page))
        click_when(page, "Settle: validators read the pool", 1200)
        log("settle: " + wait_tx(page))
        page.locator("#ag-view .badge.SETTLED").wait_for(timeout=180000)
        share_text = page.locator("#ag-view .share").text_content()
        share_bp = round(float(share_text.split("%")[0]) * 100)
        lo, hi = EXPECT[PRESET]
        page.locator("#ag-view details[data-key=copied] summary").click() if PRESET != "ghost" else None
        time.sleep(21)  # one refresh tick: the opened table must stay open on a closed agreement
        still_open = PRESET == "ghost" or page.evaluate("document.querySelector('#ag-view details[data-key=copied]').open")
        res.update(share_bp=share_bp, pass_share=lo <= share_bp <= hi, table_stays_open=still_open,
                   no_sideways=all(x[1] for x in res["steps"]) and no_sideways(page), page_errors=errors)
        res["pass"] = res["pass_share"] and res["no_sideways"] and still_open and not errors
        page.screenshot(path=OUT.replace(".json", ".png"), full_page=True)
        log(f"RESULT {'PASS' if res['pass'] else 'FAIL'} share={share_bp} sideways_ok={res['no_sideways']} table_open={still_open} errors={len(errors)}")
        ctx.close()
    with open(OUT, "w") as f:
        json.dump(res, f, indent=2)
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
