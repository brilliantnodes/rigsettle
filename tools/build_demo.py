#!/usr/bin/env python3
"""Build the fictional demo pool pages into web/public/demo/.

Everything here is FICTIONAL: Fernhollow Pool, Saltmarsh Pool, Quillmoor
Pool and Examplecoin do not exist. The pages exist so anyone can try
RigSettle end to end without a real pool, and so the daily canary has fixed
inputs. Each page's script prints per-minute rows from the clock with a
fixed formula, so every validator that reads a page sees the same numbers
for every completed minute.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "web" / "public" / "demo"

STYLE = """
body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f4f5f7;color:#16181d}
header{background:#1f2a37;color:#fff;padding:14px 20px}
header b{font-size:18px}
.tag{display:inline-block;background:#ffcc00;color:#000;font-weight:700;font-size:12px;padding:2px 8px;border-radius:4px;margin-left:8px}
main{max-width:760px;margin:0 auto;padding:16px 20px}
table{border-collapse:collapse;width:100%;background:#fff}
th,td{border-bottom:1px solid #e3e5e8;padding:6px 10px;text-align:left;font-variant-numeric:tabular-nums}
.note{color:#4b5563;font-size:13px}
.box{background:#fff;padding:14px 16px;border:1px solid #e3e5e8;border-radius:6px;margin:12px 0}
"""

COMMON_JS = r"""
function h(seed, m) {
  var x = (Math.imul(m, 2654435761) ^ Math.imul(seed, 40503)) >>> 0;
  x ^= x << 13; x >>>= 0; x ^= x >>> 17; x ^= x << 5; x >>>= 0;
  return x / 4294967296;
}
function pad(n) { return (n < 10 ? "0" : "") + n; }
function fmt(ms) {
  var d = new Date(ms);
  return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()) + " " + pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes());
}
var NOW = Date.now();
var CUR = Math.floor(NOW / 60000);
"""

WORKER_JS = r"""
function rate(m) {
  if (MODE === "steady") return 10 * (0.985 + 0.035 * h(SEED, m));
  if (MODE === "sixty") return 10 * (0.57 + 0.06 * h(SEED, m));
  if (MODE === "dark") return 10 * (0.99 + 0.02 * h(SEED, m));
  if (MODE === "outage") { var k = ((m % 10) + 10) % 10; return (k === 3 || k === 4) ? 0 : 10 * (0.995 + 0.015 * h(SEED, m)); }
  return 0;
}
var tb = document.getElementById("rows");
var cur = document.createElement("tr");
cur.innerHTML = "<td>" + fmt(CUR * 60000) + "</td><td>in progress</td>";
tb.appendChild(cur);
for (var i = 1; i <= ROWS; i++) {
  var m = CUR - i;
  var tr = document.createElement("tr");
  tr.innerHTML = "<td>" + fmt(m * 60000) + "</td><td>" + rate(m).toFixed(2) + " GH/s</td>";
  tb.appendChild(tr);
}
document.getElementById("updated").textContent = fmt(NOW) + " UTC";
"""

STATUS_JS = r"""
var ul = document.getElementById("incidents");
var shown = 0;
for (var m = CUR; m > CUR - 180 && shown < 40; m--) {
  var k = ((m % 10) + 10) % 10;
  var j = ((m % 30) + 30) % 30;
  var li = null;
  if (k === 3) {
    li = document.createElement("li");
    var end = (m + 2) * 60000;
    var resolved = end <= NOW;
    li.innerHTML = "<b>Stratum server restart</b> &ndash; mining connections dropped for all workers.<br>Start: " + fmt(m * 60000) + " UTC &middot; End: " + fmt(end) + " UTC &middot; " + (resolved ? "Resolved" : "Ongoing");
  } else if (j === 17) {
    li = document.createElement("li");
    li.innerHTML = "<b>Website dashboard maintenance</b> &ndash; charts may load slowly. Mining and stratum are not affected.<br>Start: " + fmt(m * 60000) + " UTC &middot; End: " + fmt((m + 2) * 60000) + " UTC";
  }
  if (li) { ul.appendChild(li); shown++; }
}
document.getElementById("updated").textContent = fmt(NOW) + " UTC";
"""

def page(title, body, script, cfg):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>{title}</title><style>{STYLE}</style></head>
<body>{body}
<script>{cfg}{COMMON_JS}{script}</script>
</body></html>
"""

def header(pool):
    return f'<header><b>{pool}</b><span class="tag">FICTIONAL DEMO POOL</span></header>'

FICTION = ('<p class="note">This is a fictional pool page made for the RigSettle demo. '
           '{pool} and Examplecoin do not exist. Nothing here is a real service.</p>')

def worker_page(pool, worker, mode, seed, rows=40):
    body = f"""{header(pool)}<main>
<h1>Worker statistics: {worker}</h1>
<p>Pool: <b>{pool}</b> &middot; Coin: Examplecoin (fictional) &middot; Worker: <b>{worker}</b></p>
<p>All times are UTC. Each row is one 1-minute slot. <b>Accepted hashrate</b> is measured by the pool from the shares it accepted (pool-side, not reported by the rig).</p>
<div class="box"><table><thead><tr><th>Slot start (UTC)</th><th>Accepted hashrate</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="note">Page generated at <span id="updated"></span>.</p>
{FICTION.format(pool=pool)}</main>"""
    cfg = f"var MODE={json.dumps(mode)};var SEED={seed};var ROWS={rows};"
    return page(f"{pool} - worker {worker} (fictional demo)", body, WORKER_JS, cfg)

def ghost_page(pool, worker):
    body = f"""{header(pool)}<main>
<h1>Worker statistics: {worker}</h1>
<p>Pool: <b>{pool}</b> &middot; Coin: Examplecoin (fictional)</p>
<div class="box"><p><b>Worker "{worker}" was not found on this pool.</b> No accepted shares have been recorded for this worker name.</p></div>
<p>All times are UTC. Page generated at <span id="updated"></span>.</p>
{FICTION.format(pool=pool)}</main>"""
    return page(f"{pool} - worker {worker} (fictional demo)", body, 'document.getElementById("updated").textContent = fmt(NOW) + " UTC";', "")

DARK_JS = r"""
var k = ((CUR % 10) + 10) % 10;
if (k >= 6) {
  document.getElementById("live").hidden = true;
  document.getElementById("down").hidden = false;
} else {
""" + WORKER_JS + r"""
}
document.getElementById("updated2").textContent = fmt(NOW) + " UTC";
"""


def dark_page(pool, worker, seed):
    """Readable most of the time, but the statistics service is down from
    6 to 9 minutes past every ten. A window starting on the hour is readable
    when the seller accepts and dark when settlement opens."""
    body = f"""{header(pool)}<main>
<div id="live">
<h1>Worker statistics: {worker}</h1>
<p>Pool: <b>{pool}</b> &middot; Coin: Examplecoin (fictional) &middot; Worker: <b>{worker}</b></p>
<p>All times are UTC. Each row is one 1-minute slot. <b>Accepted hashrate</b> is measured by the pool from the shares it accepted (pool-side, not reported by the rig).</p>
<div class="box"><table><thead><tr><th>Slot start (UTC)</th><th>Accepted hashrate</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="note">Page generated at <span id="updated"></span>.</p>
</div>
<div id="down" hidden>
<h1>Dashboard temporarily unavailable</h1>
<div class="box"><p>The {pool} statistics service is down for unplanned maintenance. Worker statistics cannot be shown right now. Please try again later.</p></div>
</div>
<p class="note">Demo schedule: this fictional statistics service is down from 6 to 9 minutes past every ten. Checked at <span id="updated2"></span>.</p>
{FICTION.format(pool=pool)}</main>"""
    cfg = f"var MODE=\"dark\";var SEED={seed};var ROWS=40;"
    return page(f"{pool} - worker {worker} (fictional demo)", body, DARK_JS, cfg)


def status_page(pool):
    body = f"""<header><b>{pool} status</b><span class="tag">FICTIONAL DEMO POOL</span></header><main>
<h1>Incident history: {pool}</h1>
<p>Incidents of the last three hours, newest first. All times are UTC.</p>
<div class="box"><ul id="incidents"></ul></div>
<p class="note">Page generated at <span id="updated"></span>.</p>
{FICTION.format(pool=pool)}</main>"""
    return page(f"{pool} status (fictional demo)", body, STATUS_JS, "")

def write(rel, html):
    p = OUT / rel / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html)
    print("wrote", p.relative_to(OUT.parents[2]))

if __name__ == "__main__":
    write("fernhollow/rig-steady", worker_page("Fernhollow Pool", "rig-steady", "steady", 11))
    write("fernhollow/rig-sixty", worker_page("Fernhollow Pool", "rig-sixty", "sixty", 23))
    write("fernhollow/rig-ghost", ghost_page("Fernhollow Pool", "rig-ghost"))
    write("saltmarsh/rig-outage", worker_page("Saltmarsh Pool", "rig-outage", "outage", 37))
    write("saltmarsh-status", status_page("Saltmarsh Pool"))
    write("quillmoor/rig-dark", dark_page("Quillmoor Pool", "rig-dark", 53))
