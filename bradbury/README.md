# RigSettle on Testnet Bradbury Phase 2

RigSettle also runs on **GenLayer Testnet Bradbury Phase 2** (chain 4221), whose validators use real models and real web access, with **real GEN payouts**. Recorded 15 Nov 2026 with two throwaway accounts holding faucet GEN (buyer `0x77F1…2734`, seller `0xF5d9…eDb7`); fictional pools only, on our demo pages.

- Contract: [`0xD3c85288A22FC33961eD80CcE54F7b90A0Aafcd8`](https://scan.bradbury.genlayer.com/address/0xD3c85288A22FC33961eD80CcE54F7b90A0Aafcd8) (deploy [0x906e…3c04](https://scan.bradbury.genlayer.com/tx/0x906e90c2aee013478e20f055c53fb9dfb4452b77a68718b20b4492be93da3c04), 5 of 5 validators).
- Build: [`build/rigsettle.py`](build/rigsettle.py), made from [`../contracts/rigsettle.py`](../contracts/rigsettle.py) by `port.py --pack` in [brilliantnodes/genlayer-patterns](https://github.com/brilliantnodes/genlayer-patterns/tree/main/bradbury). The GenVM v0.6 dialect needs four API renames and new imports; the code is then stripped and compressed so the deploy fits Bradbury's per-transaction gas limit. The unpacked code is [`build/rigsettle.unpacked.py`](build/rigsettle.unpacked.py); the tool asserts the syntax tree equals the source after the renames, and that the compression round trip is lossless.
- Tests: the same 163 direct-mode tests pass on GenVM v0.2 (Studio) and on GenVM v0.6 against the packed Bradbury build (genlayer-test 0.30.0rc2).

## Five cases on Bradbury (price 2 GEN, seller's bond 1 GEN)

Each agreement went through the real flow: the buyer locks the price (`create`), validators check the pool page can be read (`probe_meter`), the seller locks the bond (`accept`), then settlement after the window.

| Case | Agreement | State | Rule | Delivered | To seller (GEN) | To buyer (GEN) | Validators | Final transaction |
|---|---|---|---|---|---|---|---|---|
| Steady rig | #1 | SETTLED | G1_WITHIN_GRACE | 100.00% | 3 | 0 | 5 of 5 | [0x54b5…1892](https://scan.bradbury.genlayer.com/tx/0x54b5efca08af704602910bf1551909d264dc41177c7ea529d8fc9198c8fe1892) |
| Rig delivering about 60% | #2 | SETTLED | S2_PRO_RATA | 60.82% | 1.8246 | 1.1754 | 5 of 5 | [0x8079…85eb](https://scan.bradbury.genlayer.com/tx/0x8079ac0ce0bff825c51d718ad96b08f8c67274ebbb9410bf2dba1236497585eb) |
| Pool outage, seller adds the status page | #3 | SETTLED | G1_WITHIN_GRACE | 100.00% | 3 | 0 | 5 of 5 | [0xace0…780a](https://scan.bradbury.genlayer.com/tx/0xace03e0853eb41e7bf973e986775fca69ca7535abdb51c569963f1dfcc46780a) |
| Seller never shows | #4 | SETTLED | Z1_WORKER_NOT_LISTED | 0.00% | 0 | 3 | 5 of 5 | [0x7c03…b7a7](https://scan.bradbury.genlayer.com/tx/0x7c036d54b842f3feada13167aef38922c9ee6551cf7163c587ea6e296dafb7a7) |
| Both parties agree a 75% split | #5 | RELEASED | R1_AGREED_SPLIT | 75.00% | 2.25 | 0.75 | 5 of 5 | [0x734a…d13a](https://scan.bradbury.genlayer.com/tx/0x734af7ed08a0f31338e673f0aca3fd8fa07af555bc7e1cc1792e4db5be94d13a) |

- **Outage evidence:** after the window the seller added the fictional pool's status page ([0x3f94…a0e1](https://scan.bradbury.genlayer.com/tx/0x3f94ec66613edc775af4163896bb667f115e91b2cb6172059a5859fd7d94a0e1)); validators read it and stored two outage intervals inside the window, so the missing slots were excused and the rental counted as full delivery.
- **Payouts arrived.** Payouts are messages sent when the settling transaction is finalized, funded from that transaction's fee deposit. The seller's balance was read after all of the seller's own transactions had finalized (7.2489 GEN) and again after the four settlements finalized (15.0735 GEN): it rose by exactly **7.8246 GEN**, the sum of the seller's payouts above. Afterwards the contract holds nothing locked (`get_locked` = 0).
- Steps for the 60% case, for reference: create [0x0dcb…b1be](https://scan.bradbury.genlayer.com/tx/0x0dcbdb9f071060b2f668f2e3956b3cc629bfb6a07a91ce0fd443aaef68f0b1be), probe [0x0bb0…4fdc](https://scan.bradbury.genlayer.com/tx/0x0bb04f4df1f19cc42a39a42ab946e53eb90c8366ffd6aa59128e51b82eca4fdc), accept [0xd8c5…2826](https://scan.bradbury.genlayer.com/tx/0xd8c561aa689ec43c02fb2b6554a067c6023ef1475a0fe49130da11c7e41f2826), settle [0x8079…85eb](https://scan.bradbury.genlayer.com/tx/0x8079ac0ce0bff825c51d718ad96b08f8c67274ebbb9410bf2dba1236497585eb).

Raw values, including every transaction: [`results/live-cases.json`](results/live-cases.json). Script: [`live_cases.py`](live_cases.py).

The website at rigsettle.brilliantnodes.com stays on GenLayer Studio, where anyone can play both parties with Studio's free test accounts.
