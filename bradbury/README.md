# RigSettle on Testnet Bradbury Phase 2

On the website: [rigsettle.brilliantnodes.com/?net=bradbury](https://rigsettle.brilliantnodes.com/?net=bradbury) shows these five rentals read-only, with explorer links for every step.

RigSettle v3 (exact agreement on the payout) also runs on **GenLayer Testnet Bradbury Phase 2** (chain 4221), whose validators use real models and real web access, with **real GEN payouts**. Recorded 16 Nov 2026 with two throwaway accounts holding faucet GEN (buyer `0x77F1…2734`, seller `0xF5d9…eDb7`); fictional pools only, on our demo pages.

- Contract: [`0xa91Ee5FEe48852620E6deC87159f04Edb40312B4`](https://scan.bradbury.genlayer.com/address/0xa91Ee5FEe48852620E6deC87159f04Edb40312B4) (deploy [0xfee8…44a8](https://scan.bradbury.genlayer.com/tx/0xfee88550e63e9602df53e0984e5392babb6bdfb6d78beb0aa947d7a9d05a44a8), 5 of 5 validators).
- Build: [`build/rigsettle.py`](build/rigsettle.py), made from [`../contracts/rigsettle.py`](../contracts/rigsettle.py) by `port.py --pack` in [brilliantnodes/genlayer-patterns](https://github.com/brilliantnodes/genlayer-patterns/tree/main/bradbury). The GenVM v0.6 dialect needs four API renames and new imports; the code is then stripped and compressed so the deploy fits Bradbury's per-transaction gas limit. The unpacked code is [`build/rigsettle.unpacked.py`](build/rigsettle.unpacked.py); the tool asserts the syntax tree equals the source after the renames, and that the compression round trip is lossless.
- Tests: the same 213 direct-mode tests pass on GenVM v0.2 (Studio) and on GenVM v0.6 against the packed Bradbury build (genlayer-test 0.30.0rc2).

## Five cases on Bradbury (price 2 GEN, seller's bond 1 GEN)

Each agreement went through the real flow: the buyer locks the price (`create`), validators check the pool page can be read (`probe_meter`), the seller locks the bond (`accept`), then settlement after the window. Under v3 each validator works out the rule and share from its own copy and must match the leader exactly.

| Case | Agreement | State | Rule | Paid share | To seller (GEN) | To buyer (GEN) | Validators | Final transaction |
|---|---|---|---|---|---|---|---|---|
| Steady rig | #1 | SETTLED | G1_WITHIN_GRACE | 100.00% | 3 | 0 | 5 of 5 | [0x168c…90b7](https://scan.bradbury.genlayer.com/tx/0x168c47acb3c9a844b1214e2e8e9167c358562ec0051097cee4ace131a31b90b7) |
| Rig delivering about 60% | #2 | SETTLED | S2_PRO_RATA | 60.06% | 1.8018 | 1.1982 | 5 of 5 | [0xe565…e452](https://scan.bradbury.genlayer.com/tx/0xe56500166ea20d6305ca622cbe53a668fbbdcedc09e453604f752faa1e0fe452) |
| Pool outage, seller adds the status page | #3 | SETTLED | G1_WITHIN_GRACE | 100.00% | 3 | 0 | 5 of 5 | [0x477e…6a2e](https://scan.bradbury.genlayer.com/tx/0x477ea1db22e79152eab4d8fb229a4a3951f71e77e328f90f34d70ba626386a2e) |
| Seller never shows | #4 | SETTLED | Z1_WORKER_NOT_LISTED | 0.00% | 0 | 3 | 5 of 5 | [0x6cd6…f14b](https://scan.bradbury.genlayer.com/tx/0x6cd6df9bd6fd0cb2cb2c57d69d78b79bfa3a8626d391ea3ab850d5276974f14b) |
| Both parties agree a 75% split | #5 | RELEASED | R1_AGREED_SPLIT | 75.00% | 2.25 | 0.75 | 5 of 5 | [0xee6e…f198](https://scan.bradbury.genlayer.com/tx/0xee6eba482f5f1f473818ae75bf1eef5cb5af779cd850f4f2a7d25ac299c7f198) |

- **Outage evidence:** after the window the seller added the fictional pool's status page ([0x1191…4397](https://scan.bradbury.genlayer.com/tx/0x1191ae2a0492d371b86b393444db92eb8679d614dea2c635f46f7fec92394397)); validators agreed which slots it covers, so 2 missing slots were excused and the rental counted as full delivery.
- **Payouts arrived.** Payouts are messages sent when the settling transaction is finalized. The seller's balance was read after all of the seller's own transactions had finalized (12.3225 GEN) and again after the four settlements finalized (20.1243 GEN): it rose by exactly 7.8018 GEN, the sum of its payouts (3 + 1.8018 + 3 + 0). The release case paid at once. `get_locked()` is 0 afterwards.
- Steps for the 60% case, for reference: create [0x6bed…b48d](https://scan.bradbury.genlayer.com/tx/0x6bedf32701a889f68615c3133d7a488103c26a334d1453df2969dcd0e657b48d), probe [0xec42…3af2](https://scan.bradbury.genlayer.com/tx/0xec42d6bf4d007a91eae71a67abb99ea05bb36480d543e07030aa8cca7fcc3af2), accept [0x85e2…5dc7](https://scan.bradbury.genlayer.com/tx/0x85e2727bf1b96e9559dd751fd1e5e4ebffd58852d1255381fce561b947885dc7), settle [0xe565…e452](https://scan.bradbury.genlayer.com/tx/0xe56500166ea20d6305ca622cbe53a668fbbdcedc09e453604f752faa1e0fe452).

Raw values, including every transaction: [`results/live-cases.json`](results/live-cases.json). Script: [`live_cases.py`](live_cases.py).

The earlier Bradbury deployment (`0xD3c8…fcd8`, v2 with a 2-point tolerance, 15 Nov) is superseded. Playing both parties yourself stays on GenLayer Studio, which has free test accounts.
