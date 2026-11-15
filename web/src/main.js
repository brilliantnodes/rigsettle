import { createClient, createAccount, generatePrivateKey } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { CONTRACT_ADDRESS, NETWORK_NAME, EXPLORER_BASE, REPO_URL, DEMO, EXAMPLES } from "./config.js";

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = String(text); // always plain text
  return n;
};
const RPC = studionet.rpcUrls.default.http[0];
const reader = createClient({ chain: studionet });

// GenLayer returns maps and big integers. Amounts arrive as strings already.
function plain(v) {
  if (v instanceof Map) return Object.fromEntries([...v.entries()].map(([k, x]) => [k, plain(x)]));
  if (Array.isArray(v)) return v.map(plain);
  if (typeof v === "bigint") return Number(v);
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, plain(x)]));
  return v;
}
const read = async (functionName, args = []) => plain(await reader.readContract({ address: CONTRACT_ADDRESS, functionName, args }));
const short = (e) => String((e && (e.shortMessage || e.message)) || e).slice(0, 300);
const shortAddr = (a) => (a ? `${a.slice(0, 6)}…${a.slice(-4)}` : "");
const same = (a, b) => !!a && !!b && a.toLowerCase() === b.toLowerCase();

// ------------------------------------------------------------ amounts

function toUnits(text, decimals) {
  const s = String(text).trim();
  if (!/^\d+(\.\d+)?$/.test(s)) return null;
  const [w, f = ""] = s.split(".");
  if (f.length > decimals) return null;
  return BigInt(w) * 10n ** BigInt(decimals) + BigInt((f + "0".repeat(decimals)).slice(0, decimals));
}
function fromUnits(v, decimals, keep = 4) {
  const n = BigInt(v);
  const base = 10n ** BigInt(decimals);
  const w = n / base;
  let f = (n % base).toString().padStart(decimals, "0").slice(0, keep).replace(/0+$/, "");
  return f ? `${w}.${f}` : `${w}`;
}
const gen = (wei) => `${fromUnits(wei, 18)} GEN`;
const ghs = (hs) => `${fromUnits(hs, 9, 3)} GH/s`;

// -------------------------------------------------------------- times

const pad = (n) => String(n).padStart(2, "0");
const utc = (ts) => {
  const d = new Date(ts * 1000);
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
};
const utcFull = (ts) => new Date(ts * 1000).toISOString().replace("T", " ").slice(0, 16) + " UTC";
const nowS = () => Math.floor(Date.now() / 1000);
function inWords(secs) {
  if (secs <= 0) return "now";
  const m = Math.ceil(secs / 60);
  return m < 60 ? `in ${m} min` : `in ${Math.floor(m / 60)} h ${m % 60} min`;
}
function toLocalInput(ts) {
  const d = new Date(ts * 1000);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ----------------------------------------------------------- accounts

const roles = { buyer: null, seller: null }; // { client, address, kind }
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch {} },
  del: (k) => { try { localStorage.removeItem(k); } catch {} },
};

function showAcctError(msg) {
  $("acct-error").textContent = msg;
  $("acct-error").hidden = !msg;
}

function setRole(role, next) {
  roles[role] = next;
  $(`${role}-addr`).textContent = next ? `${next.kind}: ${next.address}` : "No account";
  if (role === "seller" && next && !$("f-seller").value) $("f-seller").value = next.address;
  refreshBalances();
  if (current) renderAgreement(current);
}

function tempAccount(role, fresh = false) {
  let key = fresh ? null : store.get(`rigsettle.temp.${role}`);
  if (!key) {
    key = generatePrivateKey();
    store.set(`rigsettle.temp.${role}`, key);
  }
  const account = createAccount(key);
  setRole(role, { client: createClient({ chain: studionet, account }), address: account.address, kind: "Temporary" });
  if (role === "seller") $("f-seller").value = account.address;
}

async function faucet(address) {
  // Studio's built-in faucet. The amount is written into the JSON by hand
  // because 100 GEN in wei is larger than a JavaScript number.
  const body = `{"jsonrpc":"2.0","id":1,"method":"sim_fundAccount","params":["${address}",100000000000000000000]}`;
  const r = await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" }, body });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message || "faucet error");
}

async function refreshBalances() {
  for (const role of ["buyer", "seller"]) {
    const r = roles[role];
    if (!r) {
      $(`${role}-bal`).textContent = "";
      continue;
    }
    try {
      const b = await reader.getBalance({ address: r.address });
      $(`${role}-bal`).textContent = `Balance: ${gen(b)}`;
    } catch {
      $(`${role}-bal`).textContent = "";
    }
  }
}

document.querySelectorAll("[data-temp]").forEach((b) => b.addEventListener("click", () => {
  showAcctError("");
  tempAccount(b.dataset.temp);
}));

document.querySelectorAll("[data-fund]").forEach((b) => b.addEventListener("click", async () => {
  const r = roles[b.dataset.fund];
  showAcctError("");
  if (!r) return showAcctError(`Choose a ${b.dataset.fund} account first.`);
  b.disabled = true;
  try {
    await faucet(r.address);
    await new Promise((x) => setTimeout(x, 2500));
    await refreshBalances();
  } catch (e) {
    showAcctError(`The faucet did not answer: ${short(e)}`);
  }
  b.disabled = false;
}));

$("btn-both").addEventListener("click", async () => {
  showAcctError("");
  $("btn-both").disabled = true;
  try {
    tempAccount("buyer");
    tempAccount("seller");
    await faucet(roles.buyer.address);
    await faucet(roles.seller.address);
    await new Promise((x) => setTimeout(x, 2500));
    await refreshBalances();
  } catch (e) {
    showAcctError(`Studio's faucet did not answer: ${short(e)}. Try again in a moment.`);
  }
  $("btn-both").disabled = false;
});

document.querySelectorAll("[data-mm]").forEach((b) => b.addEventListener("click", async () => {
  const role = b.dataset.mm;
  showAcctError("");
  if (!window.ethereum) return showAcctError("No browser wallet was found. Use a temporary account instead, or install MetaMask.");
  try {
    // Order matters: MetaMask only lets an account send on a network it was
    // approved for, so the Studio network is added first and the account is
    // approved after that.
    await useStudioNetwork();
    const accounts = await requestAccounts();
    if (!accounts || !accounts.length) throw new Error("The wallet returned no account.");
    const other = role === "buyer" ? roles.seller : roles.buyer;
    if (other && same(other.address, accounts[0])) throw new Error("This wallet account is already the other party. Use a temporary account for one side.");
    setRole(role, { client: createClient({ chain: studionet, account: accounts[0] }), address: accounts[0], kind: "MetaMask" });
  } catch (e) {
    showAcctError(`The wallet did not connect: ${short(e)}`);
  }
}));

async function requestAccounts() {
  try {
    await window.ethereum.request({ method: "wallet_requestPermissions", params: [{ eth_accounts: {} }] });
    return await window.ethereum.request({ method: "eth_accounts" });
  } catch (e) {
    if (e && e.code === 4001) throw e;
    return await window.ethereum.request({ method: "eth_requestAccounts" });
  }
}

async function useStudioNetwork() {
  const chainId = `0x${studionet.id.toString(16)}`;
  const cur = await window.ethereum.request({ method: "eth_chainId" });
  if (String(cur).toLowerCase() === chainId) return;
  try {
    await window.ethereum.request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  } catch {
    await window.ethereum.request({
      method: "wallet_addEthereumChain",
      params: [{ chainId, chainName: studionet.name, rpcUrls: studionet.rpcUrls.default.http, nativeCurrency: studionet.nativeCurrency }],
    });
    await window.ethereum.request({ method: "wallet_switchEthereumChain", params: [{ chainId }] });
  }
}

// ------------------------------------------------- transaction lifecycle

const STEPS = [
  ["SENT", "Sent", "The transaction was signed and sent."],
  ["PENDING", "Queued", "Waiting for a leader to be chosen."],
  ["PROPOSING", "Leader works", "One validator runs the method; if it reads a page, it reads it now."],
  ["COMMITTING", "Validators check", "The other validators run it on their own and vote."],
  ["REVEALING", "Votes revealed", "Votes are opened and counted."],
  ["ACCEPTED", "Accepted", "A majority agreed. The new state is recorded."],
];
const ORDER = STEPS.map((s) => s[0]);
const FINAL_BAD = {
  UNDETERMINED: "The validators did not agree, so nothing changed. This is the safe outcome when a page is unclear or changing. You can try again.",
  CANCELED: "The transaction was cancelled. Nothing changed.",
  LEADER_TIMEOUT: "The leader did not answer in time. Nothing changed. You can try again.",
  VALIDATORS_TIMEOUT: "The validators did not answer in time. Nothing changed. You can try again.",
};
const statusOf = (tx) => String(tx?.statusName ?? tx?.status_name ?? "").toUpperCase();

function drawSteps(cur, failed) {
  const ol = $("steps");
  ol.replaceChildren();
  const at = ORDER.indexOf(cur === "FINALIZED" ? "ACCEPTED" : cur);
  STEPS.forEach(([key, title, help], i) => {
    const li = el("li");
    li.className = failed && i >= Math.max(at, 0) ? (i === Math.max(at, 0) ? "failed" : "todo") : i < at ? "done" : i === at ? (key === "ACCEPTED" ? "done" : "now") : "todo";
    li.append(el("strong", null, title), el("span", null, help));
    ol.append(li);
  });
}

// The method's own answer, from the leader's receipt. Used for messages
// only: every outcome is confirmed by reading the agreement back.
function leaderAnswer(tx) {
  try {
    const lr = tx?.consensus_data?.leader_receipt;
    const r = (Array.isArray(lr) ? lr[0] : lr)?.result;
    if (!r) return null;
    if (r.status === "rollback") return { reverted: String(r.payload || "") };
    const p = r.payload;
    if (p && typeof p === "object" && "readable" in p) {
      try { return JSON.parse(p.readable); } catch { return null; }
    }
    return null;
  } catch {
    return null;
  }
}

let busy = false;
async function send(who, functionName, args, value, what) {
  if (busy) return null;
  busy = true;
  setButtons(false);
  $("life").hidden = false;
  $("life-what").textContent = what;
  $("life-hash").replaceChildren();
  $("life-note").textContent = who.kind === "MetaMask" ? "Confirm the transaction in your wallet…" : "Signing in this browser…";
  drawSteps("", false);
  $("life").scrollIntoView({ behavior: "smooth", block: "nearest" });
  const fire = () => who.client.writeContract({ address: CONTRACT_ADDRESS, functionName, args, value: value || 0n });
  let hash, err;
  try { hash = await fire(); } catch (e) { err = e; }
  // A temporary account signs in the page, so a send that failed on a brief
  // network error is repeated once. A wallet is never asked twice.
  if (err && who.kind === "Temporary") {
    $("life-note").textContent = "The network did not answer. Trying once more…";
    await new Promise((r) => setTimeout(r, 2500));
    try { hash = await fire(); err = null; } catch (e) { err = e; }
  }
  if (err) {
    drawSteps("SENT", true);
    $("life-note").textContent = err.code === 4100
      ? "Your wallet has not approved this account for the Studio network. Click MetaMask again, approve the account, and retry."
      : `The transaction was not sent: ${short(err)}`;
    busy = false;
    setButtons(true);
    return null;
  }
  const tl = el("a", null, "view on the explorer");
  tl.href = `${EXPLORER_BASE}/tx/${hash}`;
  tl.target = "_blank";
  tl.rel = "noopener noreferrer";
  $("life-hash").append(el("span", null, "Transaction: "), el("code", null, hash), el("span", null, " · "), tl);
  drawSteps("SENT", false);
  const waitNote = "Simple steps take under a minute; steps where validators read a page take one to three minutes.";
  $("life-note").textContent = `Sent. ${waitNote}`;
  let last = "SENT", final = null;
  const t0 = Date.now();
  while (Date.now() - t0 < 8 * 60 * 1000) {
    await new Promise((r) => setTimeout(r, 3000));
    $("life-note").textContent = `Sent ${Math.round((Date.now() - t0) / 1000)} s ago. ${waitNote}`;
    let tx;
    try { tx = await reader.getTransaction({ hash }); } catch { continue; }
    const st = statusOf(tx);
    if (st && st !== last && (ORDER.includes(st) || st === "FINALIZED")) {
      last = st;
      drawSteps(st, false);
    }
    if (st === "ACCEPTED" || st === "FINALIZED") { final = { ok: true, tx }; break; }
    if (FINAL_BAD[st]) { final = { ok: false, st }; break; }
  }
  busy = false;
  // The agreement's buttons stay disabled until it has been read again
  // (see after()), so a stale button cannot be pressed twice.
  refreshing = true;
  $("btn-create").disabled = false;
  if (!final) {
    $("life-note").textContent = "Not settled after eight minutes. It may still complete; press Reload on the agreement later.";
    return null;
  }
  if (!final.ok) {
    drawSteps(last, true);
    $("life-note").textContent = FINAL_BAD[final.st];
    return null;
  }
  const ans = leaderAnswer(final.tx);
  if (ans && ans.reverted) {
    drawSteps("REVEALING", true);
    $("life-note").textContent = `The contract refused this step: ${ans.reverted}`;
  } else if (ans && ans.ok === false && ans.refunded) {
    drawSteps("REVEALING", true);
    $("life-note").textContent = `The contract refused this step and sent the ${gen(ans.refunded)} straight back: ${ans.error}`;
  } else {
    $("life-note").textContent = "Accepted by a majority of validators.";
  }
  refreshBalances();
  return { hash, answer: ans };
}

let refreshing = false;
function setButtons(on) {
  document.querySelectorAll("#ag-view button, #btn-create").forEach((b) => (b.disabled = !on));
}

// ---------------------------------------------------------- the form

const PRESETS = {
  steady: { pool: "Fernhollow Pool", worker: "rig-steady", path: "fernhollow/rig-steady", note: "A rig delivering about 10 GH/s with normal pool noise. Expected: paid in full." },
  sixty: { pool: "Fernhollow Pool", worker: "rig-sixty", path: "fernhollow/rig-sixty", note: "You rented 10 GH/s; the rig delivers about 6. Expected: about 60% of the price and of the bond to the seller." },
  outage: { pool: "Saltmarsh Pool", worker: "rig-outage", path: "saltmarsh/rig-outage", note: "The pool's stratum restarts every five minutes for two minutes and lists each restart on its status page, so every five-minute window has two dead minutes. Without an outage report the seller gets about 60%; with one, the drop is excused." },
  gappy: { pool: "Fernhollow Pool", worker: "rig-gappy", path: "fernhollow/rig-gappy", note: "The rig mines only three of every five minutes, and this pool leaves minutes without shares off the page. A missing minute counts as zero, so the seller gets about 60%, not 100%." },
  ghost: { pool: "Fernhollow Pool", worker: "rig-ghost", path: "fernhollow/rig-ghost", note: "The worker never appears on the pool. Expected: the buyer gets the price and the whole bond." },
  dark: { pool: "Quillmoor Pool", worker: "rig-dark", path: "quillmoor/rig-dark", align10: true, note: "This fictional pool's statistics go down 6 to 9 minutes past every ten. The page reads fine at acceptance and is dark at settlement: nothing moves, and after the cut-off the default rule pays the seller, because the buyer controls the pool." },
};

function presetStart(align10) {
  // Leave about six minutes for the probe (usually under a minute, longer
  // when Studio is busy) and the acceptance.
  let m = Math.ceil((nowS() + 6 * 60) / 60);
  if (align10) while (m % 10) m++;
  return m * 60;
}

document.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => {
  const p = PRESETS[b.dataset.preset];
  $("f-pool").value = p.pool;
  $("f-worker").value = p.worker;
  $("f-meter").value = `${DEMO}/${p.path}/`;
  $("f-status").value = `${DEMO}/saltmarsh-status/`;
  $("f-rate").value = "10";
  $("f-slot").value = "1";
  $("f-slots").value = "5";
  $("f-start").value = toLocalInput(presetStart(p.align10));
  $("f-price").value = "10";
  $("f-bond").value = "2";
  $("f-grace").value = "3";
  $("f-evidence").value = "2";
  $("f-default").value = "12";
  if (roles.seller) $("f-seller").value = roles.seller.address;
  $("preset-note").textContent = `${p.note} The window is five 1-minute slots so the demo finishes in about 15 minutes. Real rentals use hourly slots. To watch a settlement right away, use a rental under "Ready to settle now" instead.`;
}));

function formError(msg) {
  $("form-error").textContent = msg;
  $("form-error").hidden = !msg;
}

function readForm() {
  const v = (id) => $(id).value.trim();
  const seller = v("f-seller");
  if (!/^0x[0-9a-fA-F]{40}$/.test(seller)) return { err: "Enter the seller's address (0x followed by 40 hex characters)." };
  if (roles.buyer && same(seller, roles.buyer.address)) return { err: "The seller must be a different account from the buyer." };
  const pool = v("f-pool"), worker = v("f-worker");
  if (pool.length < 2 || pool.length > 80) return { err: "Enter the pool's name as it appears on its pages (2 to 80 characters)." };
  if (!worker || worker.length > 80) return { err: "Enter the worker name (1 to 80 characters)." };
  const okUrl = (s) => { try { const u = new URL(s); return /^https?:$/.test(u.protocol) && s.length <= 300; } catch { return false; } };
  const meter = v("f-meter"), status = v("f-status");
  if (!okUrl(meter)) return { err: "Enter the pool's worker page as a full http or https address." };
  if (status && !(okUrl(status) && status.startsWith("https://") && status.endsWith("/"))) return { err: "The status site must be an https:// address ending with /." };
  const rate = toUnits(v("f-rate"), 9);
  if (!rate || rate <= 0n) return { err: "Enter the hashrate in GH/s." };
  const slot = parseInt(v("f-slot"), 10), slots = parseInt(v("f-slots"), 10);
  if (!(slots >= 3 && slots <= 96) || slots * slot > 1440) return { err: "Use 3 to 96 slots and a window of at most 24 hours." };
  const startMs = new Date(v("f-start")).getTime();
  if (!startMs) return { err: "Choose the window start." };
  const start = Math.floor(startMs / 1000);
  if (start % (slot * 60)) return { err: `The window must start on a ${slot}-minute boundary.` };
  if (start <= nowS() + 60) return { err: "The window must start in the future, with time for the seller to accept." };
  const price = toUnits(v("f-price"), 18), bond = toUnits(v("f-bond") || "0", 18);
  if (!price || price <= 0n || price > 1000n * 10n ** 18n) return { err: "Enter a price above 0 and at most 1,000 test GEN." };
  if (bond === null || bond > price) return { err: "The bond must be between 0 and the price." };
  const grace = Math.round(parseFloat(v("f-grace") || "0") * 100);
  if (!(grace >= 0 && grace <= 1000)) return { err: "Grace must be 0 to 10%." };
  const ev = parseInt(v("f-evidence") || "0", 10), df = parseInt(v("f-default") || "0", 10);
  if (!(ev >= 0 && ev <= 1440)) return { err: "The evidence window must be 0 to 1,440 minutes." };
  if (!(df >= ev + 10 && df <= 10080)) return { err: `The default rule must come at least 10 minutes after the evidence window (${ev + 10} or more).` };
  return { args: [seller, pool, worker, meter, status, rate, slot, start, slots, bond, grace, start, ev, df], price };
}

$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  formError("");
  if (!roles.buyer) return formError("Choose a buyer account first (step 1).");
  const f = readForm();
  if (f.err) return formError(f.err);
  const res = await send(roles.buyer, "create", f.args, f.price, `Create a rental and lock ${gen(f.price)}`);
  if (!res) return;
  let id = res.answer && res.answer.id;
  if (!id) {
    try {
      const mine = await read("get_by_party", [roles.buyer.address]);
      id = mine[mine.length - 1];
    } catch {}
  }
  if (id) {
    $("ag-id").value = id;
    for (let i = 0; i < 10; i++) {
      try { current = await read("get_agreement", [String(id)]); break; } catch {}
      await new Promise((r) => setTimeout(r, 3000));
    }
    refreshing = false;
    if (current && String(current.id) === String(id)) renderAgreement(current);
    else await openAgreement(id);
  }
  refreshing = false;
  loadRecent();
});

// ----------------------------------------------------------- agreement

let current = null;

async function openAgreement(id) {
  refreshing = false;
  try {
    current = await read("get_agreement", [String(id)]);
    renderAgreement(current);
  } catch (e) {
    $("ag-view").replaceChildren(el("p", "error", `Agreement ${id} could not be read: ${short(e)}`));
  }
}

function times(a) {
  const t = a.terms;
  const start = t.start_at, end = start + t.slots * t.slot_minutes * 60;
  const ev = a.evidence || {};
  const bothDone = ev.buyer && ev.seller;
  const settleAt = bothDone ? end + t.slot_minutes * 60 : Math.max(end + t.slot_minutes * 60, end + t.evidence_minutes * 60);
  return { start, end, settleAt, evidenceUntil: end + t.evidence_minutes * 60, cutoff: end + t.default_after_minutes * 60 };
}

const RULE_TEXT = {
  G1_WITHIN_GRACE: "Delivery was within the grace band for pool noise, so it counts as full.",
  S2_PRO_RATA: "The seller is paid the delivered share of the price, slot by slot, capped at the contracted rate.",
  Z1_WORKER_NOT_LISTED: "The pool page was readable but the worker never appeared: nothing was delivered.",
  D1_METER_DARK_AFTER_WINDOW: "The pool page was dark after the window and the cut-off passed. The buyer controls the pool, so the seller is paid.",
  D2_NO_READING: "No reading was produced before the cut-off and the page was never dark, so the buyer is refunded.",
  R1_AGREED_SPLIT: "Both parties named the same split.",
  CANCELLED_BY_BUYER: "The buyer cancelled before the seller accepted.",
  EXPIRED_UNACCEPTED: "The seller did not accept in time.",
};
// Short labels for lists. Every settled outcome names what happened, so a
// refund after the cut-off never reads like a failed delivery.
const RULE_LABEL = {
  G1_WITHIN_GRACE: "Full delivery (within grace)",
  S2_PRO_RATA: "Paid pro rata",
  Z1_WORKER_NOT_LISTED: "No-show: buyer refunded",
  D1_METER_DARK_AFTER_WINDOW: "Meter dark: seller paid",
  D2_NO_READING: "Refunded: nobody settled before the cut-off",
  R1_AGREED_SPLIT: "Agreed split",
  CANCELLED_BY_BUYER: "Cancelled by the buyer",
  EXPIRED_UNACCEPTED: "Expired: seller did not accept",
};
function outcomeText(a) {
  const res = a.result || {};
  if (!res.rule) return "";
  const label = RULE_LABEL[res.rule] || res.rule;
  if (res.share_bp === undefined || ["D2_NO_READING", "Z1_WORKER_NOT_LISTED"].includes(res.rule)) return label;
  return `${label} · ${(res.share_bp / 100).toFixed(2)}% to seller`;
}
const REASON_TEXT = {
  N1_METER_DARK: "the pool page could not be read as this pool's worker page (meter dark)",
  N2_FORMAT: "the page's rows did not fit the terms (times not UTC, misaligned or conflicting rows)",
  C1_COVERAGE: "fewer than half the slots were still on the page",
  READABLE: "readable",
};

function renderAgreement(a) {
  const box = $("ag-view");
  box.replaceChildren();
  const t = a.terms;
  const T = times(a);
  const me = { buyer: roles.buyer && same(roles.buyer.address, a.buyer), seller: roles.seller && same(roles.seller.address, a.seller) };
  const head = el("div", "ag-head");
  head.append(el("span", `badge ${a.state}`, a.state), el("strong", null, `#${a.id} · ${t.pool_name} · ${t.worker_name}`));
  box.append(head);
  const parties = el("p", "small");
  parties.textContent = `Buyer ${a.buyer}${me.buyer ? " (your buyer account)" : ""} · Seller ${a.seller}${me.seller ? " (your seller account)" : ""}`;
  box.append(parties);

  const dl = el("dl", "facts");
  const add = (k, v) => dl.append(el("dt", null, k), el("dd", null, v));
  add("Hashrate", ghs(t.rate_hs));
  add("Window", `${utcFull(T.start)} to ${utc(T.end)} · ${t.slots} slots of ${t.slot_minutes} min`);
  add("Price (locked)", gen(t.price));
  add("Seller's bond", gen(t.bond));
  add("Grace for noise", `${t.grace_bp / 100}%`);
  add("Accept by", utcFull(t.accept_by));
  box.append(dl);
  const src = el("p", "small src");
  src.append(el("span", null, "Meter: "), linkTo(t.meter_url));
  if (t.status_prefix) src.append(el("br"), el("span", null, "Status site: "), linkTo(t.status_prefix));
  box.append(src);

  const nx = el("div", "next");
  const acts = el("div", "actions");
  const extra = el("div");
  const anyone = roles.buyer || roles.seller;
  const btn = (label, fn, cls) => {
    const b = el("button", cls, label);
    b.type = "button";
    b.disabled = busy || refreshing;
    b.addEventListener("click", fn);
    acts.append(b);
    return b;
  };
  const now = nowS();
  // Studio can answer a read with the state from just before the new
  // transaction, so keep reading until the agreement's history has moved.
  const after = async (res) => {
    refreshing = true;
    const before = (a.history || []).length;
    for (let i = 0; i < 10; i++) {
      try {
        const fresh = await read("get_agreement", [String(a.id)]);
        current = fresh;
        if (!res || (fresh.history || []).length > before || fresh.state !== a.state) break;
      } catch {}
      await new Promise((r) => setTimeout(r, 3000));
    }
    refreshing = false;
    renderAgreement(current);
    loadRecent();
  };

  if (a.state === "OPEN") {
    const p = a.probe;
    const fresh = p && p.ok && now - p.at <= 3600;
    if (now > t.accept_by) {
      nx.textContent = "The seller did not accept in time. Anyone can return the price to the buyer.";
      if (anyone) btn("Return the price (expire)", () => send(anyone, "expire", [a.id], 0n, "Expire and refund the buyer").then(after));
    } else if (!fresh) {
      nx.textContent = `Step 1: validators confirm the pool page can be read${p && !p.ok ? ` (last check: ${REASON_TEXT[p.reason] || p.reason})` : ""}. Then the seller accepts before ${utc(t.accept_by)} (${inWords(t.accept_by - now)}).`;
      if (anyone) btn("Check the meter", () => send(roles.seller || anyone, "probe_meter", [a.id], 0n, "Validators check the pool page").then(after));
    } else {
      nx.textContent = `The meter was confirmed readable at ${utc(p.at)}. The seller can now lock the bond and accept, until ${utc(t.accept_by)} (${inWords(t.accept_by - now)}).`;
      if (me.seller) btn(`Accept and lock ${gen(t.bond)}`, () => send(roles.seller, "accept", [a.id], BigInt(t.bond), "Seller accepts and locks the bond").then(after));
      else nx.textContent += " Use the seller account to accept.";
    }
    if (me.buyer && now <= t.accept_by) btn("Cancel and refund", () => send(roles.buyer, "cancel", [a.id], 0n, "Buyer cancels").then(after), "secondary");
  } else if (a.state === "ACTIVE") {
    if (now < T.start) nx.textContent = `Accepted. The mining window starts at ${utc(T.start)} (${inWords(T.start - now)}). Point the rigs at the pool with worker name "${t.worker_name}".`;
    else if (now < T.end) nx.textContent = `The mining window is running until ${utc(T.end)} (${inWords(T.end - now)}).`;
    else if (now < T.settleAt) nx.textContent = `The window has ended. Settlement opens at ${utc(T.settleAt)} (${inWords(T.settleAt - now)}). Until ${utc(T.evidenceUntil)} each party may add one outage report or waive it.`;
    else nx.textContent = `Settlement is open. Anyone can ask the validators to read the pool page${now >= T.cutoff ? ", or apply the default rule because the cut-off has passed" : ""}.`;
    if (now >= T.settleAt && anyone) btn("Settle: validators read the pool", () => send(anyone, "settle", [a.id], 0n, "Validators read the pool page and settle").then(after));
    if (now >= T.cutoff && anyone) btn("Apply the default rule", () => send(anyone, "settle_default", [a.id], 0n, "Default rule after the cut-off").then(after), "secondary");
    // outage evidence, one per party
    const ev = a.evidence || {};
    for (const party of ["buyer", "seller"]) {
      // Each party gets one report, so offer it once the window has ended and
      // incidents in it can be resolved (from the start if there is no evidence window).
      const evidenceFrom = t.evidence_minutes > 0 ? T.end : T.start;
      if (!me[party] || ev[party] || now < evidenceFrom || now >= T.evidenceUntil || !t.status_prefix) continue;
      const wrap = el("div", "actions");
      const inp = el("input", "url");
      inp.type = "url";
      inp.value = t.status_prefix;
      inp.setAttribute("aria-label", `Outage report address (${party})`);
      const b1 = el("button", "secondary", `Add outage report (${party})`);
      b1.type = "button";
      b1.addEventListener("click", () => send(roles[party], "add_evidence", [a.id, inp.value.trim()], 0n, `Validators read the ${party}'s outage report`).then(after));
      const b2 = el("button", "link", "Waive");
      b2.type = "button";
      b1.disabled = b2.disabled = busy || refreshing;
      b2.addEventListener("click", () => send(roles[party], "waive_evidence", [a.id], 0n, `The ${party} waives an outage report`).then(after));
      wrap.append(inp, b1, b2);
      extra.append(wrap);
      extra.append(el("p", "small", `One outage report per party, read by the validators now. Use the status page that lists the incident. Open until ${utc(T.evidenceUntil)}.`));
    }
    // agreed split
    for (const party of ["buyer", "seller"]) {
      if (!me[party]) continue;
      const wrap = el("div", "actions");
      const inp = el("input");
      inp.type = "number"; inp.min = "0"; inp.max = "100"; inp.step = "0.01"; inp.value = "100";
      inp.setAttribute("aria-label", `Seller's share in percent (${party})`);
      const b = el("button", "secondary", `Propose this seller share (${party})`);
      b.type = "button";
      b.disabled = busy || refreshing;
      b.addEventListener("click", () => {
        const bp = Math.round(parseFloat(inp.value) * 100);
        if (!(bp >= 0 && bp <= 10000)) return;
        send(roles[party], "propose_release", [a.id, bp], 0n, `The ${party} proposes a ${bp / 100}% seller share`).then(after);
      });
      wrap.append(el("span", "small", "Settle now by agreement:"), inp, el("span", "small", "%"), b);
      extra.append(wrap);
    }
    const rel = a.release || {};
    if (rel.buyer !== null || rel.seller !== null) {
      extra.append(el("p", "small", `Proposed seller share: buyer ${rel.buyer === null ? "none" : rel.buyer / 100 + "%"}, seller ${rel.seller === null ? "none" : rel.seller / 100 + "%"}. The escrow splits when both match.`));
    }
  } else {
    nx.textContent = a.state === "SETTLED" || a.state === "RELEASED" ? "Closed. The escrow was split as shown below." : RULE_TEXT[a.result && a.result.rule] || "Closed.";
  }
  box.append(nx);
  if (acts.children.length) box.append(acts);
  box.append(extra);
  if (!anyone && (a.state === "OPEN" || a.state === "ACTIVE")) box.append(el("p", "small", "Choose an account in step 1 to take the next step."));

  if (a.result && (a.state === "SETTLED" || a.state === "RELEASED")) box.append(resultView(a));
  else if (a.result) {
    const r = el("p", "ok", `Returned to the buyer: ${gen(a.result.paid_buyer)}.`);
    box.append(r);
  }

  if (a.probe) box.append(el("p", "small", `Meter check: ${a.probe.ok ? "readable" : REASON_TEXT[a.probe.reason] || a.probe.reason} at ${utcFull(a.probe.at)}.`));
  const ev = a.evidence || {};
  for (const party of ["buyer", "seller"]) {
    const x = ev[party];
    if (!x) continue;
    if (x.waived) box.append(el("p", "small", `The ${party} waived an outage report.`));
    else box.append(el("p", "small", `The ${party}'s outage report (${x.url}): ${x.intervals.length ? x.intervals.map((i) => `${utc(i[0])} to ${utc(i[1])}`).join(", ") : "no qualifying mining or stratum outage in the window"}.`));
  }
  (a.attempts || []).forEach((x) => box.append(el("p", "small", `Settlement attempt at ${utcFull(x.at)}: no reading, because ${REASON_TEXT[x.reason] || x.reason}. Nothing moved.`)));

  const d = el("details");
  d.dataset.key = "history";
  d.append(el("summary", null, `History (${(a.history || []).length} steps)`));
  const ul = el("ul", "timeline");
  (a.history || []).forEach((h) => ul.append(el("li", null, `${utcFull(h.at)} · ${h.action}${h.note ? " · " + h.note : ""} · by ${shortAddr(h.by)}`)));
  d.append(ul);
  box.append(d);
}

function resultView(a) {
  const r = a.result;
  const wrap = el("div");
  const share = r.share_bp;
  wrap.append(el("div", "share", `${(share / 100).toFixed(2)}% delivered`));
  const bar = el("div", "bar");
  const fill = el("span");
  fill.style.width = `${share / 100}%`;
  bar.append(fill);
  wrap.append(bar);
  wrap.append(el("p", "why", RULE_TEXT[r.rule] || r.rule));
  if (r.raw_share_bp !== undefined && r.raw_share_bp !== share) wrap.append(el("p", "small", `Measured share before the grace band: ${(r.raw_share_bp / 100).toFixed(2)}%.`));
  const pay = el("div", "payout");
  const b1 = el("div"); b1.append(el("span", "small", "Buyer receives"), el("b", null, gen(r.paid_buyer)));
  const b2 = el("div"); b2.append(el("span", "small", "Seller receives"), el("b", null, gen(r.paid_seller)));
  pay.append(b1, b2);
  wrap.append(pay);
  wrap.append(el("p", "small", "Payouts are sent when the settlement transaction is finalized, after GenLayer's appeal window (under a minute on Studio)."));
  const rd = r.reading;
  if (rd && rd.kind === "READ" && rd.listed) {
    const t = a.terms;
    const rate = BigInt(t.rate_hs);
    const out = r.outages || [];
    const byIndex = new Map(rd.rows.map(([i, v]) => [i, v]));
    const tbl = el("table", "slots");
    const cap = el("caption", "small", "Every slot of the window. A slot the pool page did not list counts as zero.");
    tbl.append(cap);
    const hr = el("tr");
    ["Slot (UTC)", "Pool measured", "Counted"].forEach((h) => { const th = el("th", null, h); th.scope = "col"; hr.append(th); });
    tbl.append(hr);
    for (let i = 0; i < t.slots; i++) {
      const s0 = t.start_at + i * t.slot_minutes * 60;
      const down = out.some(([x, y]) => x < s0 + t.slot_minutes * 60 && y > s0);
      const listed = byIndex.has(i);
      const m = listed ? BigInt(byIndex.get(i)) : 0n;
      const counted = down && m < rate ? `${ghs(rate)} (outage excused)` : ghs(m < rate ? m : rate) + (m > rate ? " (capped)" : "");
      const tr = el("tr");
      tr.append(el("td", null, utc(s0)), el("td", null, listed ? ghs(m) : "not on the page"), el("td", null, counted));
      tbl.append(tr);
    }
    const d = el("details");
    d.dataset.key = "copied";
    d.append(el("summary", null, `What the validators copied from the pool (${rd.rows.length} of ${t.slots} slots listed)`));
    d.append(tbl);
    wrap.append(d);
  }
  return wrap;
}

function linkTo(url) {
  const a = el("a", null, url);
  if (/^https?:\/\//i.test(url)) {
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer nofollow";
  }
  return a;
}

$("btn-open").addEventListener("click", () => { const id = $("ag-id").value; if (id) openAgreement(id); });
$("btn-reload").addEventListener("click", () => { if (current) openAgreement(current.id); });
// Refresh the time-dependent text of an open agreement. Closed agreements
// never change, and a refresh must not reset what the visitor is typing or
// close a section they opened.
setInterval(() => {
  if (!current || busy || refreshing || !["OPEN", "ACTIVE"].includes(current.state)) return;
  const view = $("ag-view");
  if (view.contains(document.activeElement) && document.activeElement.tagName === "INPUT") return;
  const open = new Set([...view.querySelectorAll("details[open]")].map((d) => d.dataset.key));
  renderAgreement(current);
  view.querySelectorAll("details").forEach((d) => { if (open.has(d.dataset.key)) d.open = true; });
}, 20000);

// ------------------------------------------------------------ recent

// ------------------------------------------------- ready to settle now

async function ensureAnyAccount() {
  if (roles.buyer || roles.seller) return roles.buyer || roles.seller;
  tempAccount("buyer");
  try { await faucet(roles.buyer.address); } catch {}
  return roles.buyer;
}

async function settleReady(id) {
  const who = await ensureAnyAccount();
  $("ag-id").value = id;
  await openAgreement(id);
  const before = current ? (current.history || []).length : 0;
  const res = await send(who, "settle", [String(id)], 0n, `Validators read the pool page and settle #${id}`);
  for (let i = 0; i < 10; i++) {
    try {
      const fresh = await read("get_agreement", [String(id)]);
      current = fresh;
      if (!res || (fresh.history || []).length > before || fresh.state !== "ACTIVE") break;
    } catch {}
    await new Promise((r) => setTimeout(r, 3000));
  }
  refreshing = false;
  if (current) renderAgreement(current);
  $("ag-card").scrollIntoView({ behavior: "smooth", block: "start" });
  loadRecent();
}

function showReady(list) {
  const box = $("ready");
  box.replaceChildren();
  const now = nowS();
  // Only rentals whose whole window is still on the demo meter page (it lists
  // the last 200 minutes), so every listed rental can be settled from a reading.
  const onMeter = (a) => now < times(a).end + METER_MINUTES * 60;
  const ready = list.filter((a) => a.state === "ACTIVE" && now >= times(a).settleAt && now < times(a).cutoff && onMeter(a)).slice(0, 2);
  if (!ready.length) {
    box.append(el("p", "small", "No rental is ready this minute. A new one is created twice an hour and opens for settlement about ten minutes later. The settled cases at the top of the page need no wait."));
    return;
  }
  ready.forEach((a) => {
    const T = times(a);
    const row = el("div", "ready-row");
    row.append(el("span", null, `#${a.id} · ${a.terms.pool_name} · ${a.terms.worker_name} · window ${utc(T.start)} to ${utc(T.end)}`));
    const b = el("button", null, `Settle #${a.id} now`);
    b.type = "button";
    b.disabled = busy;
    b.addEventListener("click", () => settleReady(a.id));
    row.append(b);
    box.append(row);
  });
  box.append(el("p", "small", "Fictional rig delivering about 60%, created twice an hour by a scheduled job with two throwaway accounts. Settling uses a temporary account in this browser if you have none. The validators read the pool page in one to three minutes; the result appears below."));
}

// ------------------------------------------------ see a settlement now

const METER_MINUTES = 195; // the demo worker pages list 200 one-minute rows

function openFromList(id) {
  $("ag-id").value = id;
  openAgreement(id);
  $("ag-card").scrollIntoView({ behavior: "smooth", block: "start" });
}

function settledAt(a) {
  const h = (a.history || []).filter((x) => String(x.action).startsWith("settle"));
  return h.length ? h[h.length - 1].at : null;
}

function showLatestSettled(list) {
  const box = $("latest-settled");
  box.replaceChildren();
  const a = list.find((x) => x.state === "SETTLED" && x.result && x.result.reading && x.result.reading.kind === "READ");
  if (!a) return;
  const row = el("div", "ready-row");
  const at = settledAt(a);
  row.append(el("span", null, `Latest settlement from a live reading: #${a.id} · ${a.terms.worker_name}${at ? ` · settled ${utcFull(at)}` : ""} · ${outcomeText(a)}`));
  const b = el("button", "secondary", `Open #${a.id}`);
  b.type = "button";
  b.addEventListener("click", () => openFromList(a.id));
  row.append(b);
  box.append(row);
}

async function loadExamples() {
  const body = $("examples");
  const rows = await Promise.all(EXAMPLES.map(async (x) => {
    try { return { x, a: await read("get_agreement", [x.id]) }; } catch { return { x, a: null }; }
  }));
  body.replaceChildren();
  rows.forEach(({ x, a }) => {
    const tr = el("tr");
    const name = el("td");
    name.append(el("span", null, x.label), el("br"), el("span", "small", `#${x.id}`));
    tr.append(name);
    if (!a || !a.result) {
      tr.append(el("td", "small", "could not be read"), el("td"), el("td"));
    } else {
      const r = a.result;
      tr.append(el("td", null, RULE_LABEL[r.rule] || r.rule), el("td", null, r.share_bp !== undefined ? `${(r.share_bp / 100).toFixed(2)}%` : "–"));
      const td = el("td");
      const b = el("button", "secondary", "Open");
      b.type = "button";
      b.setAttribute("aria-label", `Open agreement ${x.id}: ${x.label}`);
      b.addEventListener("click", () => openFromList(x.id));
      td.append(b);
      tr.append(td);
    }
    body.append(tr);
  });
}

async function loadRecent() {
  $("recent-state").textContent = "Loading…";
  try {
    const all = await read("get_latest", [50]); // the contract's maximum
    showReady(all);
    showLatestSettled(all);
    const list = all.slice(0, 20);
    const box = $("recent");
    box.replaceChildren();
    $("recent-state").textContent = list.length ? `${list.length} most recent, newest first.` : "No agreements yet.";
    list.forEach((a) => {
      const b = el("button");
      b.type = "button";
      const res = a.result || {};
      b.append(el("span", `badge ${a.state}`, a.state), el("strong", null, `#${a.id}`), el("span", null, `${a.terms.pool_name} · ${a.terms.worker_name}`));
      if (res.rule) b.append(el("span", "small", outcomeText(a)));
      b.addEventListener("click", () => openFromList(a.id));
      box.append(b);
    });
  } catch (e) {
    $("recent-state").textContent = `The contract could not be read: ${short(e)}`;
  }
}
$("btn-recent").addEventListener("click", loadRecent);

async function loadRules() {
  try {
    const r = await read("get_rules");
    const rows = [
      ["Copy, don't judge", "Each validator copies the pool's per-slot accepted hashrate into a fixed form. Code does all the arithmetic."],
      ["S1 Cap", "Each slot counts at most the contracted rate. Over-delivery is never billed."],
      ["S2 Pro rata", "Delivered share = counted hashrate ÷ (contracted rate × every slot of the window)."],
      ["M1 Missing slot", `A slot the pool page does not list counts as ${r.missing_slot_counts_as}. Pools often leave idle intervals out, so averaging would pay for slots that were never mined.`],
      ["G1 Grace", `A shortfall within the agreed grace (up to ${r.max_grace_bp / 100}%) counts as full delivery.`],
      ["X1 Outage", "A slot is excused only if an outage on the named status site covers it and the meter shows the drop (a slot missing from the page counts as a drop)."],
      ["Z1 No-show", "A readable pool page that says the worker does not exist means nothing was delivered."],
      ["N1 / N2 / C1 No reading", `An unreadable page, a row that cannot be read or does not fit the terms, or fewer than ${r.min_coverage_bp / 100}% of slots on the page: nothing moves, and anyone may retry.`],
      ["D1 / D2 Default", "After the cut-off: if the page was dark, the seller is paid (the buyer controls the pool); if nobody produced a reading, the buyer is refunded."],
      ["Validator agreement", `Same outcome kind and reason, and raw shares within ${r.share_tolerance_bp / 100} percentage points; within ${r.grace_edge_tolerance_bp / 100} of a point where the grace rule would decide differently.`],
      ["Seller's bond", "Returned in proportion to the delivered share; the rest goes to the buyer."],
    ];
    const t = $("rules");
    t.replaceChildren();
    rows.forEach(([a, b]) => { const tr = el("tr"); tr.append(el("th", null, a), el("td", null, b)); t.append(tr); });
  } catch {}
}

// --------------------------------------------------------------- boot

$("net").append(el("span", "dot"), el("span", null, NETWORK_NAME));
const fc = $("foot-contract");
fc.append(el("span", null, "Contract: "));
const ca = el("a", null, CONTRACT_ADDRESS);
ca.href = `${EXPLORER_BASE}/address/${CONTRACT_ADDRESS}`;
ca.target = "_blank";
ca.rel = "noopener noreferrer";
fc.append(ca);
$("foot-repo").href = REPO_URL;
for (const role of ["buyer", "seller"]) if (store.get(`rigsettle.temp.${role}`)) tempAccount(role);
fetch("./rigsettle-demo.mp4", { method: "HEAD" }).then((r) => { if (r.ok) $("video-card").hidden = false; }).catch(() => {});
const q = new URLSearchParams(location.search).get("a");
if (q) { $("ag-id").value = q; openAgreement(q); }
loadExamples();
loadRecent();
loadRules();
