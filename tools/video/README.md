# Demo videos

`stage.html` draws every scene at a given time; `render.py` steps through the
scenes at 30 fps in headless Chromium and pipes each frame straight into
ffmpeg, one encoded file per scene, then joins them without re-encoding.

    npm install @fontsource/inter@5          # the font, from npm
    python3 shot.py 2                         # site screenshots of agreement #2
    python3 render.py data.json long          # rigsettle-demo.mp4  (1920x1080, 45 s)
    python3 render.py data.json short         # rigsettle-short.mp4 (1080x1920, 30 s)

`data.json` holds the numbers shown, copied from agreement #2 on the v2
contract (rows, share, payouts, validator votes) and from #3 and #8 for the
outage and missing-minute scenes. Every pool in the videos is fictional.
