#!/usr/bin/env python3
"""E2E: a first-time visitor with no accounts settles a rental from
"Ready to settle now" and sees the result.

  python tests/e2e/ready_flow.py <browser> <device> [site_url]
"""
import os
import sys

from playwright.sync_api import sync_playwright

BROWSER, DEVICE = sys.argv[1], sys.argv[2]
URL = sys.argv[3] if len(sys.argv) > 3 else "https://rigsettle.brilliantnodes.com/"

with sync_playwright() as p:
    proxy = {"server": os.environ["HTTPS_PROXY"]} if os.environ.get("HTTPS_PROXY") else None
    ctx_args = dict(p.devices[DEVICE]) if DEVICE != "desktop" else {"viewport": {"width": 1280, "height": 900}}
    b = getattr(p, BROWSER).launch(proxy=proxy)
    page = b.new_context(**ctx_args).new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    btn = page.locator("#ready button").first
    btn.wait_for(timeout=90000)
    label = btn.text_content()
    print("ready:", label, flush=True)
    btn.click()
    page.wait_for_function("() => /Accepted by a majority|refused|did not agree|did not answer|not sent/.test(document.getElementById('life-note').textContent)", timeout=600000)
    print("tx:", page.locator("#life-note").text_content(), flush=True)
    page.locator("#ag-view .badge.SETTLED").wait_for(timeout=120000)
    share = page.locator("#ag-view .share").text_content()
    sideways = page.evaluate("document.scrollingElement.scrollWidth <= window.innerWidth + 1")
    acct = page.locator("#buyer-addr").text_content()
    print(f"RESULT {'PASS' if sideways and not errors else 'FAIL'} {label} -> {share}; temp account: {acct[:22]}...; no sideways: {sideways}; errors: {errors}", flush=True)
    page.screenshot(path=f"/home/claude/runs/ready_{BROWSER}_{DEVICE.replace(' ', '_')}.png", full_page=False)
    b.close()
