# RigSettle

**Hashrate rentals, settled by GenLayer validators reading the buyer's pool.**

Live site: https://rigsettle.brilliantnodes.com/ · Contract (v2) on GenLayer Studio: [`0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f`](https://explorer-studio.genlayer.com/address/0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f) · MIT licence

> Test GEN on GenLayer Studio only. Every pool, worker and coin in the examples (Fernhollow Pool, Saltmarsh Pool, Quillmoor Pool, Examplecoin) is fictional.
>
> **Try it in three minutes:** open the site and use **Ready to settle now**. An hourly job keeps a finished fictional rental waiting, so you can watch the validators read the pool and split the escrow without waiting for a new window.

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
| **N2 Format** | Times not in UTC, rows off the slot grid, two different values for one slot, or a row in the window whose number or unit cannot be read (for example a decimal comma): nothing moves, because guessing would move money. |
| **C1 Coverage** | Fewer than half the slots are on the page: nothing moves. This protects a seller from a reading taken after the pool's history has rolled past the window; either party can settle as soon as settlement opens. |
| **D1 Default (dark)** | After the cut-off, if a settlement attempt found the meter dark, the seller is paid in full: the buyer controls the pool, and the probe showed it readable. |
| **D2 Default (nothing)** | After the cut-off with no reading and no dark attempt, the buyer is refunded in full. |
| **R1 Agreed split** | Both parties named the same seller share. |
| **Bond** | Returned to the seller in proportion to the delivered share; the rest goes to the buyer. |

Money is integer arithmetic in wei. For every final state the payouts add up exactly to price + bond (tested for thousands of share values and odd amounts).

## How consensus is used

- `gl.vm.run_nondet_unsafe(leader_fn, validator_fn)` for the probe, outage reports and settlement.
- A validator repeats the leader's work independently, re-validates the shape of the leader's result (a malformed or impossible result is rejected), and accepts only if:
  - both readings are the same kind (a reading, or no reading) and, for no reading, the same reason;
  - for a reading, the **raw** delivered shares differ by at most **2 percentage points**, and by at most **half a point** where the two readings fall on different sides of the grace step.
- Outage reports must agree on the set of qualifying intervals within one slot.
- "No reading" is an agreed outcome, so an unreadable page costs one round instead of a stalled transaction.
- After consensus the contract recomputes the payout from the agreed facts.
- **What a dishonest leader can do:** move the raw share by at most 2 points, and turn a reading into full pay only when the honest reading is already within half a point of the grace edge (with 3% grace: from 96.5%). Without the half-point rule, the 2-point tolerance plus the grace step would have let it lift a 95% reading to 100%. Honest validators copy the same finished rows, so in every live run they reported identical numbers; the tolerance only absorbs differences in rounding.

## Safety details

- **Payable calls never revert after money arrives.** On GenLayer Studio a reverted payable call keeps the GEN it was sent (measured: 3 GEN stayed in the contract balance with no record). So `create` and `accept` check everything first and, on any problem, send the value straight back and return the reason.
- Page text sits between delimiters that the page cannot reproduce; the model is told the page is untrusted data; it can only fill a fixed form; Python decides. A fooled leader cannot move the payout beyond the tolerance above, because honest validators copying the real numbers reject it (tested).
- **URL filter.** Refused: user names or passwords in the address, backslashes, IPv6 literals, single-label hosts (`metadata`, `localhost`), numeric tricks (`2130706433`, `0x7f.0.0.1`, `0177.0.0.1`), private, loopback, link-local (cloud metadata), shared and reserved IPv4 ranges, and `.local`, `.internal`, `.lan` and similar names. A public name that resolves to a private address cannot be seen from a contract; GenVM's network sandbox is the boundary there. A refused address at `create` sends the price straight back (shown live).
- Each agreement's history keeps its first entry and the latest 99, so repeated probes or retries cannot grow the record without limit.
- Outage reports must start with the status-site prefix frozen in the terms (`https://…/`).
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

Demo rentals use five 1-minute slots so a full lifecycle takes about 15 minutes; **Ready to settle now** skips the wait. Real rentals use hourly slots (see `examples/terms-hourly.example.json`).

LIVE_RESULTS_PLACEHOLDER

## Tests

- `PYTHONPATH=. pytest tests/direct` runs **163 direct-mode tests** (web and LLM mocked): every rule ID, every refusal path with its refund, timing gates, outage evidence, the default rules, agreed release, money invariants, validator accept/reject cases (drift, gaps, the grace edge, lying, sneaky and malformed leaders), the URL filter, number parsing, prompt delimiters, views, history capping and picklability of the non-deterministic closures.
- **Mutation check:** `PYTHONPATH=. python tools/mutate.py` breaks the contract in 46 ways (each rule, gate, refund, tolerance and filter) and runs the tests against each broken copy; all 46 are caught. The original file is never modified.
- `genvm-lint check contracts/rigsettle.py` passes.
- `tests/direct/conftest.py` patches one gap in `genlayer-test` 0.29.2: its `warp()` does not update `gl.message_raw["datetime"]`, so without the patch time-based rules could not be tested.
- `tests/e2e/site_flow.py` drives the live site with Playwright, playing both parties from create to settlement (see Site).

Setup: Python 3.12+, `pip install -r requirements.txt` (test tooling pinned to exact commits).

## Site

`web/` is a static Vite app using `genlayer-js`; `npm run build` writes to `docs/`, which GitHub Pages serves. The library sits in its own long-cached chunk (122 kB gzipped); the app itself is 11 kB gzipped and the page text renders before either loads.

- **Ready to settle now:** finished fictional rentals waiting for settlement, one click to watch the validators settle one (a temporary account is made if you have none).
- Two roles in one page: play both parties with two temporary accounts funded from Studio's built-in faucet, or connect MetaMask for one role (the Studio network is added before the account is requested).
- Every transaction shows its consensus stages, the hash with an explorer link, and a plain explanation of undetermined, timed-out and refused outcomes, including refunds.
- The agreement view shows the next step and its time, the actions each party may take, the outage reports, no-reading attempts, the full history, and after settlement the share, the payouts and every slot of the window with what the pool showed and what counted.
- Accessibility: labelled form fields, errors announced to screen readers, transaction progress in a live region, visible keyboard focus, text contrast at WCAG AA in light and dark mode, no sideways scrolling on phones.

E2E_PLACEHOLDER

The wallet path was tested with the seller on an injected EIP-1193 wallet that behaves like MetaMask where it matters: it starts on another network, refuses unknown chains until they are added, and refuses to send from an account approved before the Studio network was added (MetaMask's error 4100). The site adds the network first, then asks for the account. METAMASK_PLACEHOLDER

## Command line, canary and ready rental

- `tools/rs.py`: deploy, show and list agreements, and run a real rental from the command line (`create terms.json`, `probe`, `accept`, `evidence`, `waive`, `settle`, `default`); the terms file format is in `examples/terms-hourly.example.json`.
- `tools/live_cases.py`: runs the fictional cases live, side by side, with fresh throwaway accounts.
- `.github/workflows/canary.yml` runs `tools/canary.py` daily: a steady, a 60% and a no-show rental against the deployed contract; it fails if any outcome changes.
- `.github/workflows/ready.yml` runs `tools/ready.py` hourly: it settles, expires or defaults anything left idle (so no test GEN stays locked) and creates the next ready-to-settle rental.
- The contract address comes from `web/src/config.js` everywhere, so the site, the tools and the jobs cannot point at different deployments.

## Use

Brilliant Nodes rents hashrate on new coins' launch days. Today that happens on marketplaces that act as the judge; private launch-day deals between rig owners and buyers have no judge at all, which is the gap RigSettle fills. The path to real use:

1. **Shadow runs first.** The desk will run its own launch-day rentals through a separate, unpublished deployment at the same time, with the real pool page as the meter and the command-line client above, so RigSettle's split can be compared with the marketplace's outcome on real pools. Real pools and coins stay out of this public repository.
2. **Then private deals.** Rig owners who sell hashrate privately on launch days get RigSettle terms instead of "pay first and hope", once GenLayer runs on a network whose GEN has value.
3. **Pool compatibility check before any deal:** the pool's public worker page lists per-slot accepted hashrate in UTC, includes idle slots or marks them, and keeps the window plus the evidence window in its history. The probe confirms the first two before the seller locks a bond.

## Versions

- **v2 (current):** `0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f`. Changes after a review of v1: missing slots count as zero (M1); an unreadable row moves nothing; half-point agreement at the grace edge; a stricter URL filter; capped history.
- **v1:** `0xE74E206a60DD7e284FF3e0452DB8078a464daa11`, source on the [`v1-contract`](https://github.com/brilliantnodes/rigsettle/tree/v1-contract) branch. 30 live agreements (27 test runs and the first canary), all closed with nothing left locked. V1_PLACEHOLDER

## Licence

MIT. See `LICENSE`.
