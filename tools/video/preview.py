import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
HERE = Path(__file__).resolve().parent
data = json.loads(Path(sys.argv[1]).read_text()); w, h = map(int, sys.argv[2].split("x"))
shots = [x.split("@") for x in sys.argv[3:]]
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={"width": w, "height": h})
    page.goto((HERE / "stage.html").as_uri()); page.evaluate("document.fonts.ready")
    page.evaluate("([w, h, d]) => setup(w, h, d)", [w, h, data])
    for name, t in shots:
        page.evaluate("([n, t]) => draw(n, t, 10, false, false)", [name, float(t)])
        page.locator("#s").screenshot(path=str(HERE / f"pv_{w}x{h}_{name}_{t}.jpg"), type="jpeg", quality=85)
    b.close()
