// Two networks. Studio: free temporary accounts, try every step yourself.
// Bradbury Phase 2: GenLayer's public testnet, shown read-only. Its rentals
// were run end to end with two testnet wallets and paid out real test GEN.
export const NETWORKS = {
  studio: {
    key: "studio",
    label: "Studio",
    name: "GenLayer Studio (studionet)",
    contract: "0x8A3E961A3f8C0596F4AFf47B664dfE35A408429f",
    explorer: "https://explorer-studio.genlayer.com",
    // Agreements already settled on this contract, one per outcome, shown at
    // the top of the page so a visitor sees a settlement without waiting.
    examples: [
      { id: "42", label: "Steady rig" },
      { id: "40", label: "Rig delivering 60%" },
      { id: "41", label: "Pool hides idle minutes" },
      { id: "35", label: "Pool outage, excused" },
      { id: "43", label: "Seller never shows" },
      { id: "33", label: "Pool page goes dark" },
      { id: "7", label: "Both parties agree a split" },
    ],
  },
  bradbury: {
    key: "bradbury",
    label: "Bradbury testnet",
    name: "GenLayer Testnet Bradbury Phase 2",
    contract: "0xD3c85288A22FC33961eD80CcE54F7b90A0Aafcd8",
    explorer: "https://scan.bradbury.genlayer.com",
    rpc: "https://rpc-bradbury.genlayer.com",
    readOnly: true,
    examples: [
      { id: "1", label: "Steady rig" },
      { id: "2", label: "Rig delivering 60%" },
      { id: "3", label: "Pool outage, excused" },
      { id: "4", label: "Seller never shows" },
      { id: "5", label: "Both parties agree a split" },
    ],
  },
};
// Bradbury transactions of each example rental (from bradbury/results/live-cases.json).
NETWORKS.bradbury.txs = {
  "1": [
    [
      "Create",
      "0x5be065f33a8db5ac8b3b30921a00c6ea915396b16150e73a799184f182265cf3"
    ],
    [
      "Pool check",
      "0x08b0f7341250b9e1b4c09a4a165df1099e54cded6c2ce7d1d1a50fe69caebea1"
    ],
    [
      "Accept",
      "0xdea2f4c8ec588f1aabb2e9b84ffe6542abdc9c6c9de10f132fd5fc5a555d3db2"
    ],
    [
      "Settle and pay out",
      "0x54b5efca08af704602910bf1551909d264dc41177c7ea529d8fc9198c8fe1892"
    ]
  ],
  "2": [
    [
      "Create",
      "0x0dcbdb9f071060b2f668f2e3956b3cc629bfb6a07a91ce0fd443aaef68f0b1be"
    ],
    [
      "Pool check",
      "0x0bb04f4df1f19cc42a39a42ab946e53eb90c8366ffd6aa59128e51b82eca4fdc"
    ],
    [
      "Accept",
      "0xd8c561aa689ec43c02fb2b6554a067c6023ef1475a0fe49130da11c7e41f2826"
    ],
    [
      "Settle and pay out",
      "0x8079ac0ce0bff825c51d718ad96b08f8c67274ebbb9410bf2dba1236497585eb"
    ]
  ],
  "3": [
    [
      "Create",
      "0x96253f588b379424f81a5e8dee64c7b075c9881dab2fd949cecdf280be29dfe2"
    ],
    [
      "Pool check",
      "0x82d6046ba1f765a22ba91383f3d84ed0dc624834cc1645888e37242ec28364c6"
    ],
    [
      "Accept",
      "0x246276e51b37efc63a19aa9e30bdc426d7a21375fb19cf4b265826223c89444b"
    ],
    [
      "Outage report",
      "0x3f94ec66613edc775af4163896bb667f115e91b2cb6172059a5859fd7d94a0e1"
    ],
    [
      "Settle and pay out",
      "0xace03e0853eb41e7bf973e986775fca69ca7535abdb51c569963f1dfcc46780a"
    ]
  ],
  "4": [
    [
      "Create",
      "0x3ff488ce8dd4de02741481d144f755d0a6cd99e7703c1d4cc805c12dc4c7f75a"
    ],
    [
      "Pool check",
      "0xc4c2c3e2faea58ed2b7e2bd393b553de916cf398ace0ba1492aab9f5cfb82a55"
    ],
    [
      "Accept",
      "0x7376d600c6de73a9a9e3a005c8763c570329853084c864e2bbaa8b7f5fac694c"
    ],
    [
      "Settle and pay out",
      "0x7c036d54b842f3feada13167aef38922c9ee6551cf7163c587ea6e296dafb7a7"
    ]
  ],
  "5": [
    [
      "Create",
      "0xe679463cfb45626971d9b3e2871a9780bb7508fd634a8fa674c17d06b3954932"
    ],
    [
      "Pool check",
      "0x5a6b1978997975febc87da5ef26d39ddc71fd0650a05a96f04e0a791b4236e0f"
    ],
    [
      "Accept",
      "0x2785003fcf13a314bed032702a113f5e2d82450e714889f6c3b414a2ed5e86e2"
    ],
    [
      "Buyer agrees split",
      "0x58964c0d64280c2f8ccffe07c0c9497a7cde3d70d6f2b8e102b62b1fda1e6eca"
    ],
    [
      "Seller agrees split, pay out",
      "0x734af7ed08a0f31338e673f0aca3fd8fa07af555bc7e1cc1792e4db5be94d13a"
    ]
  ]
};
export const NET = NETWORKS[new URLSearchParams(location.search).get("net")] || NETWORKS.studio;
export const CONTRACT_ADDRESS = NET.contract;
export const NETWORK_NAME = NET.name;
export const EXPLORER_BASE = NET.explorer;
export const EXAMPLES = NET.examples;
export const REPO_URL = "https://github.com/brilliantnodes/rigsettle";
export const DEMO = "https://rigsettle.brilliantnodes.com/demo";
