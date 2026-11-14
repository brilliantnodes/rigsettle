import os, sys
from playwright.sync_api import sync_playwright
aid = sys.argv[1]
proxy = {"server": os.environ["HTTPS_PROXY"]}
with sync_playwright() as p:
    b = p.chromium.launch(proxy=proxy)
    for name, vw, scale in (("shot_long.jpg", 1000, 2), ("shot_short.jpg", 430, 3)):
        pg = b.new_page(viewport={"width": vw, "height": 1400}, device_scale_factor=scale)
        pg.goto(f"https://rigsettle.brilliantnodes.com/?a={aid}", wait_until="domcontentloaded", timeout=60000)
        pg.locator("#ag-view .share").wait_for(timeout=90000)
        pg.locator("#ag-view details[data-key=copied] summary").click()
        pg.wait_for_timeout(800)
        el = pg.locator("#ag-view")
        el.screenshot(path=name, type="jpeg", quality=92)
        box = el.bounding_box()
        print(name, box["width"], box["height"], round(box["height"] / box["width"], 4))
        pg.close()
    b.close()
