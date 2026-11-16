// Two networks. Studio: free temporary accounts, try every step yourself.
// Bradbury Phase 2: GenLayer's public testnet, shown read-only. Its rentals
// were run end to end with two testnet wallets and paid out real test GEN.
export const NETWORKS = {
  studio: {
    key: "studio",
    label: "Studio",
    name: "GenLayer Studio (studionet)",
    contract: "0x918635F13907c1C0C8CED56d0f14e2bc9b516DC3",
    explorer: "https://explorer-studio.genlayer.com",
    // Agreements already settled on this contract, one per outcome, shown at
    // the top of the page so a visitor sees a settlement without waiting.
    examples: [
      { id: "1", label: "Steady rig" },
      { id: "2", label: "Rig delivering 60%" },
      { id: "6", label: "Pool hides idle minutes" },
      { id: "3", label: "Pool outage, excused" },
      { id: "5", label: "Seller never shows" },
      { id: "12", label: "Pool page goes dark" },
      { id: "10", label: "Both parties agree a split" },
    ],
  },
  bradbury: {
    key: "bradbury",
    label: "Bradbury testnet",
    name: "GenLayer Testnet Bradbury Phase 2",
    contract: "0xa91Ee5FEe48852620E6deC87159f04Edb40312B4",
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
      "0xde5bb65feec9a1e59262790a3fbaa6da7debe45f6f868670a13545d2e98878c5"
    ],
    [
      "Pool check",
      "0x4ce358f0c84e9f2e78d5040a4ce382856789485d3ee6ffc771a1ef2980732200"
    ],
    [
      "Accept",
      "0xa87c70f6605c646c7cdced9970abf280409e85f0cc6c8886652d76d0405b4ca1"
    ],
    [
      "Settle and pay out",
      "0x168c47acb3c9a844b1214e2e8e9167c358562ec0051097cee4ace131a31b90b7"
    ]
  ],
  "2": [
    [
      "Create",
      "0x6bedf32701a889f68615c3133d7a488103c26a334d1453df2969dcd0e657b48d"
    ],
    [
      "Pool check",
      "0xec42d6bf4d007a91eae71a67abb99ea05bb36480d543e07030aa8cca7fcc3af2"
    ],
    [
      "Accept",
      "0x85e2727bf1b96e9559dd751fd1e5e4ebffd58852d1255381fce561b947885dc7"
    ],
    [
      "Settle and pay out",
      "0xe56500166ea20d6305ca622cbe53a668fbbdcedc09e453604f752faa1e0fe452"
    ]
  ],
  "3": [
    [
      "Create",
      "0xfdfccb02d77e6b96287feac1e4d4c7e1b162cc8375ae6eb0248bcd7ae3434217"
    ],
    [
      "Pool check",
      "0xe7261174a9bdbdc25fd0ed35ce89a19d17aed251c1984b690dad1609be7f6ed3"
    ],
    [
      "Accept",
      "0x36bd6ccff3c0b1753f392590a36ddb567992a609b23c35af94450e0da0bcfb4d"
    ],
    [
      "Outage report",
      "0x1191ae2a0492d371b86b393444db92eb8679d614dea2c635f46f7fec92394397"
    ],
    [
      "Settle and pay out",
      "0x477ea1db22e79152eab4d8fb229a4a3951f71e77e328f90f34d70ba626386a2e"
    ]
  ],
  "4": [
    [
      "Create",
      "0xaef61cfec12f359646f7a09de77bb504925f1abc33d3ebd8175358e51a3c8262"
    ],
    [
      "Pool check",
      "0x133436bb5eca9951ce2f2ad2151ba8ce106476c74508f165b51b823b7a9e10bd"
    ],
    [
      "Accept",
      "0x2b94b5e47b8a64561f01d84395a8f3e2599de5277769edbd16229ff604d69230"
    ],
    [
      "Settle and pay out",
      "0x6cd6df9bd6fd0cb2cb2c57d69d78b79bfa3a8626d391ea3ab850d5276974f14b"
    ]
  ],
  "5": [
    [
      "Create",
      "0xb6ce3a48ecb7a3e1ab0ea8e1a64e1580865896355aae8e6b02cb66fb592531b0"
    ],
    [
      "Pool check",
      "0x7f4a40e539d43ae75f49f9fb7fafd3d3e07e76bc92ee9b72a300d5bb3727cddb"
    ],
    [
      "Accept",
      "0x315bc0cee30dabd2dcc38879167c19b5b55b237dbc2483814c8bbb66aad1f0e3"
    ],
    [
      "Buyer agrees split",
      "0x6644e197c2c2674b49b8a7899eb2ace0ed62fc10e5b4312ef606392375f2bbbc"
    ],
    [
      "Seller agrees split, pay out",
      "0xee6eba482f5f1f473818ae75bf1eef5cb5af779cd850f4f2a7d25ac299c7f198"
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
