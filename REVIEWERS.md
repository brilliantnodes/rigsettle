# RigSettle: start here (for reviewers, 5 minutes)

**What it is, in plain words:** escrow for renting mining power (hashrate) in a private deal. The seller's rigs mine into the buyer's own pool, so the pool's public worker page is a meter neither side can edit. When the rental ends, GenLayer validators read that page and plain code pays the seller only for the share actually delivered. Market context: Bitcoin miners alone are projected to have earned about $17.2bn in 2025 ([The Block](https://www.theblock.co/post/383997/2026-bitcoin-mining-outlook)).

## 1. How consensus binds the money

- **The model copies; code decides.** Each validator reads the worker page itself; its model copies the per-slot accepted hashrate into a fixed form. Every rule (cap, pro rata, missing slot counts as zero, grace band, outage, no-show, dark meter, coverage, defaults) is deterministic Python: README, [The rule table](README.md#the-rule-table-code-not-the-model).
- **Exact agreement on the payout (v3).** A validator accepts the leader only if the rule and the paid share worked out from each copy, with the outages on record, are exactly equal. The payout is a pure function of that share, so every reading the network can accept pays exactly the same amounts. README, [How consensus is used](README.md#how-consensus-is-used).
- **"No reading" is an agreed outcome**, so an unreadable page costs one round, never a stalled transaction; after the cut-off only a default rule can apply.
- **Integer money.** Payouts are in wei and add up exactly to price + bond in every final state; transfers run only when the settlement is finalized, after the appeal window.

## 2. Check it in five steps

1. Open the site: https://rigsettle.brilliantnodes.com. **See a settlement now** opens one settled agreement for every outcome, with the per-minute values the validators copied.
2. Import the contract into GenLayer Studio: [`0x6955…C68D`](https://studio.genlayer.com/?import-contract=0x695563599bCFFA6FFE0DEfab906735a939E7C68D) and call `get_rules()`.
3. Settle one yourself: **Watch a live settlement** (a finished fictional rental is kept waiting twice an hour; one to three minutes), or start a rental with free temporary accounts.
4. Read the Studio results table in the README ([Live results on Studio (v3)](README.md#live-results-on-studio-v3)): steady 100%, about 60% paid 60.26%, idle minutes hidden 59.82%, outage with report 100% and without 60.00%, no-show 0%, dark page default, agreed split 75%.
5. The same v3 contract on Testnet Bradbury: [`0xa91E…12B4`](https://scan.bradbury.genlayer.com/address/0xa91Ee5FEe48852620E6deC87159f04Edb40312B4), five cases, each step agreed by 5 of 5 validators ([`bradbury/README.md`](bradbury/README.md)).

## 3. Links

- Video: https://www.youtube.com/watch?v=f3gmJecyeSU
- Source: [`contracts/rigsettle.py`](contracts/rigsettle.py)

*Every pool, worker and coin in the examples is fictional. Test GEN only.*
