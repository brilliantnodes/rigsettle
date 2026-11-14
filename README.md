# RigSettle

**Hashrate rentals, settled by GenLayer validators reading the buyer's pool.**

Live site: https://rigsettle.brilliantnodes.com/ · Contract on GenLayer Studio: [`0xE74E206a60DD7e284FF3e0452DB8078a464daa11`](https://explorer-studio.genlayer.com/address/0xE74E206a60DD7e284FF3e0452DB8078a464daa11) · MIT licence

> Test GEN on GenLayer Studio only. Every pool, worker and coin in the examples (Fernhollow Pool, Saltmarsh Pool, Quillmoor Pool, Examplecoin) is fictional.

## The trust problem

When someone rents hashrate in a private deal (a new coin's launch day, a Discord or forum offer), the buyer pays first and hopes. Disputes go nowhere: *"you sent 6 of the 10 GH/s I paid for"*, *"your pool was down, not my rigs"*. Marketplaces solve this only inside their own walls, with their own staff as the judge.

RigSettle needs no judge on either side. The seller's rigs mine to the **buyer's** pool, so the pool's public worker page is a meter that neither party can write to. The payment sits in an Intelligent Contract. When the window ends, GenLayer validators each read that page, copy the numbers into a fixed form, and plain Python splits the escrow by what was delivered.

## How it works

1. **Create.** The buyer names the seller, the pool, the worker, the pool's worker page, the hashrate, the window and a bond, and locks the price (`create`, payable). The terms are frozen.
2. **Probe.** Validators confirm the worker page belongs to the named pool, uses UTC and can be read (`probe_meter`). The worker need not be listed yet.
3. **Accept.** Within 60 minutes of a passing probe and before the window starts, the named seller locks the bond (`accept`, payable).
4. **Mine.** The seller's rigs mine to the buyer's pool under the agreed worker name.
5. **Outage report (optional).** Either party may record one page from the pool's status site named in the terms (`add_evidence`), or waive it.
6. **Settle.** One slot after the window ends (and after the evidence window), anyone calls `settle`. Each validator reads the worker page and copies the per-slot **accepted** hashrate. Code computes the delivered share and pays out.
7. **Or agree.** At any time both parties may name the same seller share (`propose_release`) and the escrow splits at once.

Payouts are transfer messages that run when the settlement transaction is **finalized**, after GenLayer's appeal window, so an appeal can still change the outcome before any GEN moves.

## The rule table (code, not the model)

The model only copies numbers from the page. Every decision is deterministic Python in `contracts/rigsettle.py`, and validators must reach the same answer.

| Rule | What happens |
|---|---|
| **S1 Cap** | Each slot counts at most the contracted rate. Over-delivery is never billed. |
| **S2 Pro rata** | Delivered share = counted hashrate ÷ (contracted rate × metered slots). Missing slots take the average of metered ones. |
| **G1 Grace** | A shortfall within the agreed grace (0–10%, default 3%) counts as full delivery. Pools *estimate* hashrate from shares, so a perfect rig shows ±1–3% noise. |
| **X1 Outage** | A slot is excused only if an outage on the status site named in the terms covers it **and** the meter shows the drop in that slot. Website-only incidents do not count. |
| **Z1 No-show** | A readable page of the named pool saying the worker does not exist means nothing was delivered. |
| **N1 Meter dark** | The page cannot be read, is the wrong pool, or says statistics are unavailable: nothing moves; anyone may retry. |
| **N2 Format** | Times not in UTC, rows off the slot grid, or two different values for one slot: nothing moves. |
| **C1 Coverage** | Fewer than half the slots are still on the page: nothing moves. |
| **D1 Default (dark)** | After the cut-off, if a settlement attempt found the meter dark, the seller is paid in full: the buyer controls the pool, and the probe showed it readable. |
| **D2 Default (nothing)** | After the cut-off with no reading and no dark attempt, the buyer is refunded in full. |
| **R1 Agreed split** | Both parties named the same seller share. |
| **Bond** | Returned to the seller in proportion to the delivered share; the rest goes to the buyer. |

Money is integer arithmetic in wei. For every final state the payouts add up exactly to price + bond (tested for thousands of share values and odd amounts).

## How consensus is used

- `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` for the probe, outage reports and settlement.
- A validator repeats the leader's work independently, re-validates the shape of the leader's result (a malformed or impossible result is rejected), and accepts only if:
  - both readings are the same kind (a reading, or no reading) and, for no reading, the same reason;
  - for a reading, the **raw** delivered shares differ by at most **2 percentage points** (compared before the grace band, so a vote cannot split at the grace edge).
- Outage reports must agree on the set of qualifying intervals within one slot.
- "No reading" is an agreed outcome, so an unreadable page costs one round instead of a stalled transaction.
- After consensus the contract recomputes the payout from the agreed facts.

## Safety details

- **Payable calls never revert after money arrives.** On GenLayer Studio a reverted payable call keeps the GEN it was sent (measured: 3 GEN stayed in the contract balance with no record). So `create` and `accept` check everything first and, on any problem, send the value straight back and return the reason.
- Page text sits between delimiters that the page cannot reproduce; the model is told the page is untrusted data; it can only fill a fixed form; Python decides. One fooled model cannot raise a payout, because honest validators copying the real numbers reject it (tested).
- URLs to private, loopback and cloud-metadata addresses are refused.
- Outage reports must start with the status-site prefix frozen in the terms (`https://…/`).
- The contract tracks `locked` (GEN owed to open agreements); tests assert it returns to zero.
- Do not send GEN to the contract without calling a method: plain transfers are not accepted.

## Fictional demo world

Hosted with the site under [`/demo/`](https://rigsettle.brilliantnodes.com/demo/fernhollow/rig-steady/), built by `tools/build_demo.py`. Each page's script prints per-minute rows from the clock with a fixed formula, so every validator sees the same numbers for every finished minute.

| Page | Behaviour |
|---|---|
| Fernhollow `rig-steady` | about 10 GH/s with normal noise |
| Fernhollow `rig-sixty` | about 6 GH/s |
| Fernhollow `rig-ghost` | "worker not found" |
| Saltmarsh `rig-outage` | 10 GH/s except 0 at 3 and 4 minutes past every ten |
| Saltmarsh status page | lists a stratum restart at 3–5 past every ten, plus website-only notices |
| Quillmoor `rig-dark` | readable, but the statistics service is down 6–9 minutes past every ten |

Demo rentals use five 1-minute slots so a full lifecycle takes about 15 minutes. Real rentals use hourly slots.

## Live results on Studio

Contract `0xE74E206a60DD7e284FF3e0452DB8078a464daa11`, 14 November 2026. Every rental used the fictional demo pools, five 1-minute slots, a 10 GEN price and a 2 GEN bond. Each case ran at least twice, from the command line (`tools/live_cases.py`) and through the site in five browser profiles.

| # | Case | Run through | Measured | Paid share | Rule | Buyer / seller GEN |
|---|---|---|---|---|---|---|
| #1 | Steady rig | command line | 99.46% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #2 | Rig delivering about 60% | command line | 60.54% | 60.54% | `S2_PRO_RATA` | 4.7352 / 7.2648 |
| #3 | Pool outage, with outage report | command line | 99.90% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #4 | Pool outage, no report | command line | 59.90% | 59.90% | `S2_PRO_RATA` | 4.812 / 7.188 |
| #5 | Seller never shows: never accepted | command line (created; the run stopped on a Studio 502 before acceptance) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #6 | Pool page goes dark: never accepted | command line (probe found the page dark; the seller's bond was sent back) | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #7 | Both parties agree a split | command line | – | 75.00% | `R1_AGREED_SPLIT` | 3 / 9 |
| #8 | Steady rig | command line | 99.78% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #9 | Rig delivering about 60% | command line | 59.76% | 59.76% | `S2_PRO_RATA` | 4.8288 / 7.1712 |
| #10 | Pool outage, with outage report | command line | 99.96% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #11 | Pool outage, no report | command line | 59.96% | 59.96% | `S2_PRO_RATA` | 4.8048 / 7.1952 |
| #12 | Seller never shows | command line | 0.00% | 0.00% | `Z1_WORKER_NOT_LISTED` | 12 / 0 |
| #13 | Pool page goes dark | command line | – | 100.00% | `D1_METER_DARK_AFTER_WINDOW` | 0 / 12 |
| #14 | Both parties agree a split | command line | – | 75.00% | `R1_AGREED_SPLIT` | 3 / 9 |
| #15 | Rig delivering about 60% | site, Pixel 7 | 60.30% | 60.30% | `S2_PRO_RATA` | 4.764 / 7.236 |
| #16 | Pool outage, with outage report | site (outage report filed there); settled by CLI | 99.96% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #17 | Rig delivering about 60% | site, Chrome | 60.30% | 60.30% | `S2_PRO_RATA` | 4.764 / 7.236 |
| #18 | Rig delivering about 60% | site, iPhone 15 | 60.30% | 60.30% | `S2_PRO_RATA` | 4.764 / 7.236 |
| #19 | Rig delivering about 60% | site, WebKit | 60.30% | 60.30% | `S2_PRO_RATA` | 4.764 / 7.236 |
| #20 | Rig delivering about 60% | site, Firefox (before the read fix); settled by CLI | 59.78% | 59.78% | `S2_PRO_RATA` | 4.8264 / 7.1736 |
| #21 | Rig delivering about 60% | site, Firefox | 59.54% | 59.54% | `S2_PRO_RATA` | 4.8552 / 7.1448 |
| #22 | Pool outage, with outage report | site, Chrome, outage report filed there | 99.84% | 100.00% | `G1_WITHIN_GRACE` | 0 / 12 |
| #23 | Rig delivering about 60%: never accepted | wallet-path test, stopped by a test-harness error | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #24 | Rig delivering about 60%: never accepted | wallet-path test, debug run | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #25 | Rig delivering about 60%: never accepted | wallet-path test, debug run | – | – | `EXPIRED_UNACCEPTED` | 10 / 0 |
| #26 | Rig delivering about 60% | site, seller on the injected wallet | 60.06% | 60.06% | `S2_PRO_RATA` | 4.7928 / 7.2072 |
| #27 | Buyer cancels before acceptance | command line | – | – | `CANCELLED_BY_BUYER` | 10 / 0 |

What the runs show:

- **Same input, same outcome.** The steady rig was paid in full every time (measured 99.46% and 99.78%, inside the 3% grace band). The 60% rig settled between 59.54% and 60.54% across nine runs (command line, five browser profiles and the wallet path), each accepted by a majority of validators.
- **Outage evidence works both ways.** On the same fictional pool, rentals without an outage report settled at 59.90% and 59.96%. With the seller's report from the pool's status page, the two restart minutes were excused and all four such rentals settled at 100%, two of them with the report filed through the site.
- **The safe paths work live.** A dark pool page gave "no reading" and moved nothing; after the cut-off the default rule paid the seller (#13). When the probe found that page dark before acceptance, the seller's bond was sent straight back (#6, then expired). Expiry refunded every unaccepted rental, and a buyer's cancel refunded the price (#27).
- **Money is exact.** Wallet balances after finalization match the contract's numbers to the wei (for #2: buyer 50 → 40 → 44.7352 GEN, seller 50 → 48 → 55.2648 GEN). After all 27 agreements closed, the contract's balance is exactly 0 GEN, equal to `get_locked()`: nothing is trapped, including the refunded acceptance.
- Studio's gateway sometimes answers 502 for a few seconds; the command-line client retries, and the site retries a dropped send once for temporary accounts.

## Tests

- `PYTHONPATH=. pytest tests/direct` runs **122 direct-mode tests** (web and LLM mocked): every rule ID, every refusal path with its refund, timing gates, outage evidence, the default rules, agreed release, money invariants, validator accept/reject cases (drift, gaps, lying and malformed leaders), prompt delimiters, parsing, views and picklability of the non-deterministic closures.
- **Mutation check:** 35 deliberate breakages of the contract (each rule, each gate, each refund) were each caught by at least one test.
- `genvm-lint check contracts/rigsettle.py` passes with no warnings.
- `tests/direct/conftest.py` patches one gap in `genlayer-test` 0.29.2: its `warp()` does not update `gl.message_raw["datetime"]`, so without the patch time-based rules could not be tested.

Setup: Python 3.12+, `pip install -r requirements.txt`.

## Site

`web/` is a static Vite app using `genlayer-js`; `npm run build` writes to `docs/`, which GitHub Pages serves.

- Two roles in one page: play both parties with two temporary accounts funded from Studio's built-in faucet, or connect MetaMask for one role (the Studio network is added before the account is requested).
- Every transaction shows its consensus stages, the hash with an explorer link, and a plain explanation of undetermined, timed-out and refused outcomes, including refunds.
- The agreement view shows the next step and its time, the actions each party may take, the outage reports, no-reading attempts, the full history, and after settlement the share, the payouts and the per-slot numbers the validators copied.

Tested end to end through the site (both parties: create → probe → accept → settle) against the live contract in Chrome, Firefox, WebKit, an iPhone 15 profile and a Pixel 7 profile, with no sideways scrolling, plus an outage report filed through the site. Firefox exposed one real bug, now fixed: right after a transaction, Studio can still answer reads with the previous state, so the site keeps reading until the agreement's history has moved.

The wallet path was tested with the seller on an injected EIP-1193 wallet that behaves like MetaMask where it matters: it starts on another network, refuses unknown chains until they are added, and refuses to send from an account approved before the Studio network was added (MetaMask's error 4100). The site adds the network first, then asks for the account, and the seller probed and accepted through it. The same connection code passed with the real MetaMask extension in our first GenLayer project.

## Command line and canary

- `tools/rs.py`: deploy, show and list agreements.
- `tools/live_cases.py`: runs the fictional cases live, side by side, with fresh throwaway accounts.
- `.github/workflows/canary.yml` runs `tools/canary.py` daily: a steady, a 60% and a no-show rental against the deployed contract; it fails if any outcome changes.

## Use

Brilliant Nodes rents hashrate for new coin launches. RigSettle is the escrow for private launch-day deals where neither side knows the other. Real deals run on a separate deployment; anything public uses the fictional pools above.

## Licence

MIT. See `LICENSE`.
