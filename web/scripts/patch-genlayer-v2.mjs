// genlayer-js 2.0.0-rc.2 estimates fees with a FeeManager call that has no
// sender, which fails on Bradbury Phase 2 ("insufficient funds for 0x0").
// Pass the connected account until upstream fixes it. Runs after npm install;
// fails the install if the code it patches has changed.
import fs from "node:fs";
const f = new URL("../node_modules/genlayer-js-v2/dist/index.js", import.meta.url);
const from = "publicClient.call({ to: address, data, gasPrice: receiptGasPrice";
const to = "publicClient.call({ account: client.account?.address, to: address, data, gasPrice: receiptGasPrice";
let s = fs.readFileSync(f, "utf8");
if (s.includes(to)) process.exit(0);
if (!s.includes(from)) { console.error("genlayer-js-v2: fee-estimate code not found; check the patch"); process.exit(1); }
fs.writeFileSync(f, s.replace(from, to));
console.log("genlayer-js-v2: fee-estimate fix applied");
