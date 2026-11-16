# RigSettle

**Hashrate rentals, settled by GenLayer validators reading the buyer's pool.**

Live site: https://rigsettle.brilliantnodes.com/ · Contract (v3, exact agreement) on GenLayer Studio: [`0x695563599bCFFA6FFE0DEfab906735a939E7C68D`](https://explorer-studio.genlayer.com/address/0x695563599bCFFA6FFE0DEfab906735a939E7C68D) · MIT licence

> Test GEN only, on GenLayer Studio and Testnet Bradbury Phase 2. Every pool, worker and coin in the examples (Fernhollow Pool, Saltmarsh Pool, Quillmoor Pool, Examplecoin) is fictional.
>
> **See a result with no wait:** open the site. **See a settlement now** lists one agreement already settled on chain for every outcome (steady, 60%, idle minutes hidden, outage excused, no-show, page dark, agreed split) and the latest settlement from a live reading; each opens instantly. To watch validators settle one live (one to three minutes), use **Watch a live settlement**: a scheduled job keeps a finished fictional rental waiting twice an hour.

## The trust problem

When someone rents hashrate in a private deal (a new coin's launch day, a Discord or forum offer), the buyer pays first and hopes. Disputes go nowhere: *"you sent 6 of the 10 GH/s I paid for"*, *"your pool was down, not my rigs"*. Marketplaces solve this only inside their own walls, with their own staff as the judge.

RigSettle needs no judge on either side. The seller's rigs mine to the **buyer's** pool, so the pool's public worker page is a meter that neither party can write to. The payment sits in an Intelligent Contract. When the window ends, GenLayer validators each read that page, copy the numbers into a fixed form, and plain Python splits the escrow by what was delivered.

## How it works

1. **Create.** The buyer names the seller, the pool, the worker, the pool's worker page, the hashrate, the window and a bond, and locks the price (`create`, payable). The terms are frozen.
2. **Probe.** Validators confirm the worker page belongs to the named pool, uses UTC and can be read (`probe_meter`). The worker need not be listed yet.
3. **Accept.** Within 60 minutes of a passing probe and before the window starts, the named seller locks the bond (`accept`, payable).
4. **Mine.** The seller's rigs mine to the buyer's pool under the agreed worker name.
5. **Outage report (optional).** Either party may record one page from the pool's status site named in the terms (`add_evidence`), or waive it.
6. **Settle.** One slot after the window ends (and after the evidence window, unless both parties added or waived a report), anyone calls `settle`. Each validator reads the worker page and copies the per-slot **accepted** hashrate. Code computes the delivered share and pays out.
7. **Or agree.** At any time both parties may name the same seller share (`propose_release`) and the escrow splits at once.

Payouts are transfer messages that run when the settlement transaction is **finalized**, after GenLayer's appeal window, so an appeal can still change the outcome before any GEN moves.

## The rule table (code, not the model)

The model only copies numbers from the page. Every decision is deterministic Python in `contracts/rigsettle.py`, and validators must reach the same answer.

| Rule | What happens |
|---|---|
| **S1 Cap** | Each slot counts at most the contracted rate. Over-delivery is never billed. |
| **S2 Pro rata** | Delivered share = counted hashrate ÷ (contracted rate × every slot of the window). |
| **M1 Missing slot** | A slot the page does not list counts as zero. Many pools leave idle intervals out of a worker's history, so an average would pay a seller who idles every other hour as if every hour was mined (shown live with the `rig-gappy` page). |
| **G1 Grace** | A shortfall within the agreed grace (0–10%, default 3%) counts as full delivery. Pools *estimate* hashrate from shares, so a perfect rig shows ±1–3% noise. |
| **X1 Outage** | A slot is excused only if an outage on the status site named in the terms covers it **and** the meter shows the drop in that slot (a slot missing from the page counts as a drop). Website-only incidents do not count. |
| **Z1 No-show** | A readable page of the named pool saying the worker does not exist means nothing was delivered. |
| **N1 Meter dark** | The page cannot be read, is the wrong pool, or says statistics are unavailable: nothing moves; anyone may retry. |
| **N2 Format** | Times not in UTC, rows off the slot grid, two different values for one slot, or a row in the window whose number or unit cannot be read (for example a decimal comma): nothing moves, because guessing would move money. A row shown as offline and copied as a bare `0` counts as zero for that slot, not as a format error. |
| **C1 Coverage** | Fewer than half the slots are on the page: nothing moves. This protects a seller from a reading taken after the pool's history has rolled past the window; either party can settle as soon as settlement opens. |
| **D1 Default (dark)** | After the cut-off, if a settlement attempt after the window ever found the meter dark (kept permanently as `dark_at`), the seller is paid in full: the buyer controls the pool, and the probe showed it readable. |
| **D2 Default (nothing)** | After the cut-off with no reading and no dark attempt, the buyer is refunded in full. After the cut-off `settle` is refused, so only D1 or D2 can apply and the order of two transactions cannot choose between a reading and a default. |
| **R1 Agreed split** | Both parties named the same seller share. |
| **Bond** | Returned to the seller in proportion to the delivered share; the rest goes to the buyer. |

Money is integer arithmetic in wei. For every final state the payouts add up exactly to price + bond (tested for thousands of share values and odd amounts).

## How consensus is used

- `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` for the probe, outage reports and settlement.
- A validator repeats the leader's work independently, re-validates the shape of the leader's result (a malformed or impossible result is rejected), and accepts only if:
  - both readings are the same kind (a reading, or no reading) and, for no reading, the same reason;
  - for a reading, the worker is listed in both or neither, and the **rule and the paid share worked out from each copy, with the outages on record, are exactly equal**. The payout is a pure function of the share, so **every reading validators can accept pays exactly the same amounts**.
- Outage reports must cover **exactly the same slots** of the window (the only thing a report feeds into the settlement).
- Only what decides the money is compared. Two copies that pay the same (for example both inside the grace band) agree; copies that would pay even one basis point differently do not, and nothing moves. The rows stored with a settlement are therefore the leader's copy, bound to produce the agreed outcome; the raw share and slot counts shown beside it come from that copy.
- "No reading" is an agreed outcome, so an unreadable page costs one round instead of a stalled transaction.
- After consensus the contract recomputes the payout from the agreed facts.
- **What a dishonest leader can do:** nothing to the payout. It cannot move the share by any amount, because validators accept only the share they compute themselves. It can only cause "no agreement", which moves nothing; anyone may retry until the default cut-off (D1/D2).
- **Changed in v3.** v2 accepted raw shares up to 2 points apart (half a point at the grace edge) and paid by the leader's number. A GenLayer steward rejected the same pattern in our MeterReader contract: two readings validators would both accept could pay differently. v3 binds the payout exactly, outage reports by covered slots, converts numbers with integer arithmetic only (floats turned 8.014 PH/s into 1 H/s less than a contracted 8.014 PH/s), and keeps the first dark reading after the window permanently for rule D1 (v2 looked only at the last 20 attempts). All 11 live cases still settle with the stricter agreement (below).

## Safety details

- **Payable calls never revert after money arrives.** On GenLayer Studio a reverted payable call keeps the GEN it was sent (measured: 3 GEN stayed in the contract balance with no record). So `create` and `accept` check everything first and, on any problem, send the value straight back and return the reason.
- Page text sits between delimiters that the page cannot reproduce; the model is told the page is untrusted data; it can only fill a fixed form; Python decides. A fooled leader cannot move the payout at all, because honest validators copying the real numbers reject any share they would not pay themselves (tested).
- **URL filter.** Refused: user names or passwords in the address, backslashes, IPv6 literals, single-label hosts (`metadata`, `localhost`), numeric tricks (`2130706433`, `0x7f.0.0.1`, `0177.0.0.1`), private, loopback, link-local (cloud metadata), shared and reserved IPv4 ranges, and `.local`, `.internal`, `.lan` and similar names. A public name that resolves to a private address cannot be seen from a contract; GenVM's network sandbox is the boundary there. A refused address at `create` sends the price straight back (shown live).
- Each agreement's history keeps its first entry and the latest 99, so repeated probes or retries cannot grow the record without limit.
- Outage reports must start with the status-site prefix frozen in the terms (`https://…/`), and can be filed only after the window ends, so a report cannot be used up early.
- **Timing, stated plainly.** Settlement opens one slot after the window ends and, unless both parties have added or waived an outage report, once the evidence window (`evidence_minutes`, fixed in the terms) has passed. Either party may settle from then until the cut-off, so either can have the page read promptly. The seller sees `evidence_minutes` before accepting; it should be shorter than the time the pool keeps the window on the worker page, or a reading may come too late (fewer than half the slots: C1, then the default). A dark page found by any settle attempt after the window arms D1 for good, because a dark meter is on the buyer's side.
- **What is stored.** The listed flag, the rule and the share are agreed by the validators from their own copies and decide the payout. The rows, raw share and slot counts stored beside them are the leader's copy, bound to produce that outcome; so are the outage intervals of a report, for which validators agree on the slots covered. `get_rules`, each settlement record and the site say so.
- The contract tracks `locked` (GEN owed to open agreements); tests assert it returns to zero.
- Send GEN only through `create` and `accept`. The contract has no method for plain transfers.

## Fictional demo world

Hosted with the site under [`/demo/`](https://rigsettle.brilliantnodes.com/demo/fernhollow/rig-steady/), built by `tools/build_demo.py`. Each page's script prints per-minute rows from the clock with a fixed formula, so every validator sees the same numbers for every finished minute.

| Page | Behaviour |
|---|---|
| Fernhollow `rig-steady` | about 10 GH/s with normal noise |
| Fernhollow `rig-sixty` | about 6 GH/s |
| Fernhollow `rig-ghost` | "worker not found" |
| Fernhollow `rig-gappy` | about 10 GH/s in three of every five minutes; the pool leaves the idle minutes off the page |
| Saltmarsh `rig-outage` | 10 GH/s except 0 in two of every five minutes (3 and 4 past each five) |
| Saltmarsh status page | lists each stratum restart (two minutes, every five minutes) and some website-only notices |
| Quillmoor `rig-dark` | readable, but the statistics service is down 6–9 minutes past every ten |

Demo rentals use five 1-minute slots so a full lifecycle takes about 15 minutes; **See a settlement now** shows finished ones and **Watch a live settlement** skips the wait for a new window. Real rentals use hourly slots (see `examples/terms-hourly.example.json`).

## Also on Testnet Bradbury Phase 2, with real payouts

The same v3 contract (GenVM v0.6 build; the same 213 tests pass on both runtimes) is live on Bradbury Phase 2 at [`0xa91E…12B4`](https://scan.bradbury.genlayer.com/address/0xa91Ee5FEe48852620E6deC87159f04Edb40312B4). Five cases went through the full flow there, each step agreed by 5 of 5 validators: steady rig 100%, rig at about 60% paid 60.06%, a pool outage excused by the status page 100%, a seller who never showed 0%, and an agreed 75% split. After the settlements finalized, the seller's balance rose by exactly the sum of its payouts (7.8018 GEN). Details and transaction links: [`bradbury/README.md`](bradbury/README.md).

The website shows this record too: switch to **Bradbury testnet** at the top of the page, or open [rigsettle.brilliantnodes.com/?net=bradbury](https://rigsettle.brilliantnodes.com/?net=bradbury). It is read-only there (no wallet needed); each rental lists every step with a link to the Bradbury explorer. Trying the steps yourself stays on Studio, which has free temporary accounts.

## Live results on Studio (v3)

Contract `0x918635F13907c1C0C8CED56d0f14e2bc9b516DC3`, 16 November 2026. Every rental used the fictional demo pools, five 1-minute slots, a 10 GEN price and a 2 GEN bond. The table is printed from the chain by `tools/results_table.py`; only the "Run through" column is written by hand.

| # | Case | Run through | Measured | Paid share | Rule | Buyer / seller GEN |
|---|---|---|---|---|---|---|
| #1 | Steady rig | command line | 99.72% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #2 | Rig delivering about 60% | command line | 60.26% | 60.26% | `S2_PRO_RATA` | 4.7688 / 7.2312 |
| #3 | Pool outage, with outage report | command line | 100.00% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #4 | Pool outage, no report | command line | 60.00% | 60.00% | `S2_PRO_RATA` | 4.8 / 7.2 |
| #5 | Seller never shows | command line | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |
| #6 | Rig idles 2 of 5 minutes, pool hides them | command line | 59.82% | 59.82% | `S2_PRO_RATA` | 4.8216 / 7.1784 |
| #7 | Buyer cancels before acceptance | command line | – | – | `CANCELLED_BY_BUYER` | 10 / 0 |
| #8 | Never accepted: expired | command line | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #9 | Pool page goes dark | command line (meant as the dark-page case; Studio queued its settle until the page was back up, so it settled from a normal reading) | 99.86% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #10 | Both parties agree a split | command line | – | 75.00% | `R1_AGREED_SPLIT` | 3 / 9 |
| #11 | Buyer cancels before acceptance | command line (a create with a cloud-metadata URL and an accept with the wrong bond were both refused and refunded first) | – | – | `CANCELLED_BY_BUYER` | 10 / 0 |
| #12 | Pool page goes dark | command line (dark-page case rerun on its own) | – | 100.00% | `D1_METER_DARK_AFTER_WINDOW` | 0 / 12 |

What the runs show:

- **Exact agreement settles in practice.** Every reading-based case reached agreement with v3's rule (validators must reach the same rule and share from their own copies): steady 100%, about 60% paid 60.26%, idle minutes hidden 59.82%, outage with report 100% and without 60.00%, no-show 0%.
- **The safe paths still work.** A dark page gave "no reading"; after the cut-off the default rule paid the seller (#12). #9 shows why the cut-off rule matters: it was meant to read the dark page, but Studio's queue delayed the transaction until the page was back, so it settled from a real reading. Refused requests were refunded (#11), an unaccepted rental expired (#8), cancels refunded the price, and the agreed split paid 75% (#10).
- **Money is exact.** For every closed agreement the payouts add up to exactly what was locked, and `get_locked()` is 0.

<details>
<summary>v2 results (14 Nov 2026, the earlier contract with a 2-point tolerance; superseded)</summary>

Contract `0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f`, 14 November 2026. Every rental used the fictional demo pools, five 1-minute slots, a 10 GEN price and a 2 GEN bond. The table is printed from the chain by `tools/results_table.py`; only the "Run through" column is written by hand.

| # | Case | Run through | Measured | Paid share | Rule | Buyer / seller GEN |
|---|---|---|---|---|---|---|
| #1 | Steady rig | command line | 99.50% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #2 | Rig delivering about 60% | command line | 59.98% | 59.98% | `S2_PRO_RATA` | 4.8024 / 7.1976 |
| #3 | Pool outage, with outage report | command line | 100.00% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #4 | Pool outage, no report | command line | 60.00% | 60.00% | `S2_PRO_RATA` | 4.8 / 7.2 |
| #5 | Seller never shows | command line | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |
| #6 | Never accepted: expired | command line (probe fell in the page's dark minutes or behind a busy queue, so acceptance was refused and the bond sent back) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #7 | Both parties agree a split | command line | – | 75.00% | `R1_AGREED_SPLIT` | 3 / 9 |
| #8 | Rig idles 2 of 5 minutes, pool hides them | command line | 59.92% | 59.92% | `S2_PRO_RATA` | 4.8096 / 7.1904 |
| #9 | Buyer cancels before acceptance | command line | – | – | `CANCELLED_BY_BUYER` | 10 / 0 |
| #10 | Never accepted: expired | command line | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #11 | Buyer cancels before acceptance | command line (a create with a metadata URL and an accept with the wrong bond were both refused and refunded first) | – | – | `CANCELLED_BY_BUYER` | 10 / 0 |
| #12 | Rig delivering about 60% | hourly ready rental; settled from "Ready to settle now" by a first-time visitor (site, iPhone 15 profile, no accounts) | 60.22% | 60.22% | `S2_PRO_RATA` | 4.7736 / 7.2264 |
| #13 | Rig delivering about 60% | site, Chrome | 60.22% | 60.22% | `S2_PRO_RATA` | 4.7736 / 7.2264 |
| #14 | Rig idles 2 of 5 minutes, pool hides them | site, Firefox | 59.96% | 59.96% | `S2_PRO_RATA` | 4.8048 / 7.1952 |
| #15 | Pool outage, no report | site, WebKit (test script stopped early; closed by the hourly job) | – | 0.00% | `D2_NO_READING` | 12 / 0 |
| #16 | Steady rig | site, Pixel 7 | 99.70% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #17 | Rig delivering about 60% | site, iPhone 15 | 60.22% | 60.22% | `S2_PRO_RATA` | 4.7736 / 7.2264 |
| #18 | Never accepted: expired | command line (probe fell in the page's dark minutes or behind a busy queue, so acceptance was refused and the bond sent back) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #19 | Pool outage, no report | site, WebKit (test script stopped early; closed by the hourly job) | – | 0.00% | `D2_NO_READING` | 12 / 0 |
| #20 | Pool outage, with outage report | command line | 99.98% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #21 | Pool outage, no report | command line | 59.98% | 59.98% | `S2_PRO_RATA` | 4.8024 / 7.1976 |
| #22 | Never accepted: expired | site, Firefox (test script stopped after the first waiver; settled from the command line) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #23 | Rig delivering about 60% | command line | 62.16% | 62.16% | `S2_PRO_RATA` | 4.5408 / 7.4592 |
| #24 | Never accepted: expired | site, Chrome (test script stopped early; closed by the hourly job) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #25 | Steady rig | command line | 99.02% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #26 | Rig idles 2 of 5 minutes, pool hides them | command line | 60.00% | 60.00% | `S2_PRO_RATA` | 4.8 / 7.2 |
| #27 | Never accepted: expired | site, Pixel 7 (test script stopped after the first waiver; settled from the command line) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #28 | Seller never shows | command line | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |
| #29 | Never accepted: expired | site, iPhone 15 (test script stopped after the first waiver; settled from the command line) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #30 | Steady rig | daily canary (GitHub Actions) | 99.02% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #31 | Rig delivering about 60% | daily canary (GitHub Actions) | 62.16% | 62.16% | `S2_PRO_RATA` | 4.5408 / 7.4592 |
| #32 | Seller never shows | daily canary (GitHub Actions) | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |
| #33 | Pool page goes dark | command line | – | 100.00% | `D1_METER_DARK_AFTER_WINDOW` | 0 / 12 |
| #35 | Pool outage, with outage report | site, WebKit (test script stopped after the outage report; settled from the command line) | 99.86% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #36 | Rig delivering about 60% | site, Firefox (test script stopped after the first waiver; settled from the command line) | 60.94% | 60.94% | `S2_PRO_RATA` | 4.6872 / 7.3128 |
| #37 | Rig idles 2 of 5 minutes, pool hides them | site, Pixel 7 (test script stopped after the first waiver; settled from the command line) | 59.88% | 59.88% | `S2_PRO_RATA` | 4.8144 / 7.1856 |
| #38 | Steady rig | site, iPhone 15 (test script stopped after the first waiver; settled from the command line) | 99.48% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #39 | Pool outage, with outage report | site, WebKit | 99.92% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #40 | Rig delivering about 60% | site, Firefox | 59.64% | 59.64% | `S2_PRO_RATA` | 4.8432 / 7.1568 |
| #41 | Rig idles 2 of 5 minutes, pool hides them | site, Pixel 7 | 59.84% | 59.84% | `S2_PRO_RATA` | 4.8192 / 7.1808 |
| #42 | Steady rig | site, iPhone 15 | 99.76% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #43 | Seller never shows | site, Chrome | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |

#34 is the hourly ready rental that was waiting for a visitor when this table was printed; the hourly job keeps one open.

What the runs show:

- **Same input, same outcome.** The steady rig was paid in full every time (measured 99.02% to 99.76%, inside the 3% grace band). The 60% rig settled between 59.64% and 62.16% across eight runs (the fictional page draws 5.7 to 6.3 GH/s each minute, so 57% to 63% is possible), each accepted by the voting validators.
- **Missing minutes count as zero (new in v2).** On the page that leaves idle minutes out, all five runs paid 59.84% to 60.00%. Under v1's averaging rule the same page would have paid 100%.
- **Outage evidence works both ways.** Without a report, the pool's two restart minutes cost the seller (59.98% and 60.00%). With the seller's report from the status page, all four rentals settled at 100%, two of them with the report filed through the site.
- **The safe paths work live.** A dark page gave "no reading" and moved nothing; after the cut-off the default rule paid the seller (#33). A create with a cloud-metadata URL and an accept with the wrong bond were both refused and refunded (#11). Expiry refunded every unaccepted rental, a buyer's cancel refunded the price, and the agreed split paid 75% (#7).
- **Abandoned rentals close themselves.** Browser tests stopped by a busy Studio queue left rentals behind; the hourly job expired the unaccepted ones and applied the default rule to two that passed their cut-off (#15, #19).
- **Money is exact.** For every closed agreement the payouts add up to exactly what was locked (the price, plus the bond once accepted), and `get_locked()` equals what the one open ready rental holds (12 GEN).
- Studio's gateway sometimes answers 502 for a few seconds, and once cancelled a settlement transaction outright (nothing moved; the retry settled). The command-line tools retry; the site explains both outcomes and lets the visitor try again.

</details>

## Tests

- `PYTHONPATH=. pytest tests/direct` runs **213 direct-mode tests** (web and LLM mocked): every rule ID, every refusal path with its refund, timing gates, outage evidence, the default rules (including a dark reading followed by 21 failed attempts, settle refused after the cut-off, and a cut-off that always leaves time to settle), agreed release, money invariants, validator accept/reject cases (a tenth of a point of drift refused, the grace edge, the outages on record applied by the validator, lying, sneaky and malformed leaders), exact number conversion, the URL filter, prompt delimiters, views, history capping and picklability of the non-deterministic closures.
- **Mutation check:** `PYTHONPATH=. python tools/mutate.py` breaks the contract in 63 ways (each rule, gate, refund, agreement check and filter; among them v2's 2-point tolerance put back, a validator that ignores the outages on record, and float conversion) and runs the tests against each broken copy; all 63 are caught. The original file is never modified.
- `genvm-lint check contracts/rigsettle.py` passes.
- `tests/direct/conftest.py` patches one gap in `genlayer-test` 0.29.2: its `warp()` does not update `gl.message_raw["datetime"]`, so without the patch time-based rules could not be tested.
- `tests/e2e/site_flow.py` drives the live site with Playwright, playing both parties from create to settlement (see Site).

Setup: Python 3.12+, `pip install -r requirements.txt` (test tooling pinned to exact commits).

## Site

`web/` is a static Vite app using `genlayer-js`; `npm run build` writes to `docs/`, which GitHub Pages serves. The library sits in its own long-cached chunk (122 kB gzipped); the app itself is 11 kB gzipped and the page text renders before either loads.

- **See a settlement now:** one settled agreement per outcome, plus the latest settlement from a live reading; each opens instantly, with no transaction.
- **Watch a live settlement:** finished fictional rentals waiting for settlement, one click to watch the validators settle one (a temporary account is made if you have none). Only rentals whose whole window is still on the demo meter page are listed; the demo worker pages show the last 200 minutes, longer than the 180-minute cut-off, so every listed rental can be settled from a reading.
- Two roles in one page: play both parties with two temporary accounts funded from Studio's built-in faucet, or connect MetaMask for one role (the Studio network is added before the account is requested).
- Every transaction shows its consensus stages, the hash with an explorer link, and a plain explanation of undetermined, timed-out and refused outcomes, including refunds.
- The agreement view shows the next step and its time, the actions each party may take, the outage reports, no-reading attempts, the full history, and after settlement the share, the payouts and every slot of the window with what the pool showed and what counted.
- Accessibility: labelled form fields, errors announced to screen readers, transaction progress in a live region, visible keyboard focus, text contrast at WCAG AA in light and dark mode, no sideways scrolling on phones.

Tested end to end through the site with `tests/e2e/site_flow.py` (both parties: create → probe → accept → waive or outage report → settle) against the v2 contract in Chrome, Firefox, WebKit (Safari's engine), an iPhone 15 profile and a Pixel 7 profile: steady, 60%, missing-minute, outage-with-report and no-show rentals all settled through the UI with the expected share, no sideways scrolling, no page errors, and the opened slot table still open after a refresh. `tests/e2e/ready_flow.py` checked that a first-time visitor with no accounts can settle a ready rental from the card (#12). The runs found and fixed three real issues: buttons were briefly clickable on the old state after a transaction (now disabled until the agreement is read again), the outage-report button was offered before the incident could be resolved (now after the window), and the ready card looked at too few agreements under load.

The wallet path was tested with the seller on an injected EIP-1193 wallet that behaves like MetaMask where it matters: it starts on another network, refuses unknown chains until they are added, and refuses to send from an account approved before the Studio network was added (MetaMask's error 4100). The site adds the network first, then asks for the account. The same connection code passed with the real MetaMask extension in our first GenLayer project.

## Command line, canary and ready rental

- `tools/rs.py`: deploy, show and list agreements, and run a real rental from the command line (`create terms.json`, `probe`, `accept`, `evidence`, `waive`, `settle`, `default`); the terms file format is in `examples/terms-hourly.example.json`.
- `tools/live_cases.py`: runs the fictional cases live, side by side, with fresh throwaway accounts.
- `.github/workflows/canary.yml` runs `tools/canary.py` daily: a steady, a 60% and a no-show rental against the deployed contract; it fails if any outcome changes.
- `.github/workflows/ready.yml` runs `tools/ready.py` twice an hour (07 and 37 minutes past; GitHub sometimes skips a scheduled run): it settles, expires or defaults anything left idle (so no test GEN stays locked) and creates the next ready-to-settle rental.
- The contract address comes from `web/src/config.js` everywhere, so the site, the tools and the jobs cannot point at different deployments.

## Use

Brilliant Nodes rents hashrate on new coins' launch days. Today that happens on marketplaces that act as the judge; private launch-day deals between rig owners and buyers have no judge at all, which is the gap RigSettle fills. The path to real use:

1. **Shadow runs first.** The desk will run its own launch-day rentals through a separate, unpublished deployment at the same time, with the real pool page as the meter and the command-line client above, so RigSettle's split can be compared with the marketplace's outcome on real pools. Real pools and coins stay out of this public repository.
2. **Then private deals.** Rig owners who sell hashrate privately on launch days get RigSettle terms instead of "pay first and hope", once GenLayer runs on a network whose GEN has value.
3. **Pool compatibility check before any deal:** the pool's public worker page lists per-slot accepted hashrate in UTC, includes idle slots or marks them, and keeps the window plus the evidence window in its history. The probe confirms the first two before the seller locks a bond.

## Versions

- **v2 (current):** `0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f`. Changes after a review of v1: missing slots count as zero (M1); an unreadable row moves nothing; half-point agreement at the grace edge; a stricter URL filter; capped history.
- **v1:** `0xE74E206a60DD7e284FF3e0452DB8078a464daa11`, source on the [`v1-contract`](https://github.com/brilliantnodes/rigsettle/tree/v1-contract) branch. 30 live agreements (27 test runs and the first canary), all closed with nothing left locked. Its README with all v1 live results is on that branch.

## Licence

MIT. See `LICENSE`.
