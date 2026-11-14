#!/usr/bin/env python3
"""Render the RigSettle videos from stage.html.

Each scene is drawn frame by frame in headless Chromium, screenshots go
straight into ffmpeg as JPEG (no frame files on disk), one encoded file per
scene, then the scenes are joined with the concat demuxer and -c copy.

  python3 render.py data.json long|short [scene ...]   (run from this folder)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
FPS = 30
PLANS = {
    "long": dict(size=(1920, 1080), out="rigsettle-demo.mp4", scenes=[
        ("hook", 4.5), ("question", 3.0), ("lock", 5.0), ("meter", 4.5), ("validators", 6.5),
        ("payout", 5.0), ("outage", 4.5), ("missing", 3.5), ("site", 5.5), ("end", 3.0)]),
    "short": dict(size=(1080, 1920), out="rigsettle-short.mp4", scenes=[
        ("hook", 4.0), ("lock", 4.5), ("validators", 6.0), ("payout", 5.0), ("site", 6.0), ("end", 4.5)]),
}


def encode_scene(page, name, dur, idx, total, outdir):
    n = round(dur * FPS)
    tmp = outdir / f"{idx:02d}_{name}.part.mp4"
    final = outdir / f"{idx:02d}_{name}.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-movflags", "+faststart", str(tmp)],
        stdin=subprocess.PIPE)
    fade_in = idx > 0
    fade_out = idx < total - 1
    for f in range(n):
        t = f / FPS
        page.evaluate("([n, t, d, a, b]) => draw(n, t, d, a, b)", [name, t, dur, fade_in, fade_out])
        ff.stdin.write(page.locator("#s").screenshot(type="jpeg", quality=92))
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit(f"ffmpeg failed on {name}")
    os.replace(tmp, final)
    return final


def main():
    data = json.loads(Path(sys.argv[1]).read_text())
    plan = PLANS[sys.argv[2]]
    only = set(sys.argv[3:])
    w, h = plan["size"]
    outdir = HERE / f"build_{sys.argv[2]}"
    outdir.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        page.goto((HERE / "stage.html").as_uri())
        page.evaluate("document.fonts.ready")
        page.evaluate("([w, h, d]) => setup(w, h, d)", [w, h, data])
        files = []
        for i, (name, dur) in enumerate(plan["scenes"]):
            f = outdir / f"{i:02d}_{name}.mp4"
            if not only or name in only or not f.exists():
                print("render", name, flush=True)
                f = encode_scene(page, name, dur, i, len(plan["scenes"]), outdir)
            files.append(f)
        b.close()
    lst = outdir / "list.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in files))
    out = HERE / plan["out"]
    tmp = out.with_suffix(".part.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    "-movflags", "+faststart", str(tmp)], check=True)
    os.replace(tmp, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
