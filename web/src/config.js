// Where the contract lives. Change these values after a new deployment.
export const CONTRACT_ADDRESS = "0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f";
export const NETWORK_NAME = "GenLayer Studio (studionet)";
export const EXPLORER_BASE = "https://explorer-studio.genlayer.com";
export const REPO_URL = "https://github.com/brilliantnodes/rigsettle";
export const DEMO = "https://rigsettle.brilliantnodes.com/demo";
// Agreements already settled on this contract, one per outcome, shown at the
// top of the page so a visitor sees a validator settlement without waiting.
export const EXAMPLES = [
  { id: "42", label: "Steady rig" },
  { id: "40", label: "Rig delivering 60%" },
  { id: "41", label: "Pool hides idle minutes" },
  { id: "35", label: "Pool outage, excused" },
  { id: "43", label: "Seller never shows" },
  { id: "33", label: "Pool page goes dark" },
  { id: "7", label: "Both parties agree a split" },
];
