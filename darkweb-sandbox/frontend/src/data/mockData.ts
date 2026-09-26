import { ListingItem, RecentItem, Vendor, CircuitHop, ForumThread } from '../types';

export const INITIAL_LISTINGS: ListingItem[] = [
  {
    id: 'listing-1',
    title: 'EU Passport (Scanned)',
    category: 'Documents',
    price: 150,
    vendor: 'nightjar_',
    rating: 4.8,
    ratingCount: 112,
    imageType: 'passport',
    description: 'High-resolution dual 600DPI scans (MRZ & front biometric page). Synthetic test passport templates intended for KYC verification bypass testing in sandbox environments.',
    specs: [
      { label: 'Format', value: 'TIFF / PDF 600DPI Uncompressed' },
      { label: 'MRZ Checksum', value: 'ICAO Doc 9303 Compliant' },
      { label: 'Delivery', value: 'PGP Encrypted Mega Link' },
      { label: 'Escrow', value: 'Standard 48hr Hold' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nRelease: EU-DOC-2025.09-NJ\nSigned-by: nightjar_ <9F42 E018 7AC3>\n-----BEGIN PGP SIGNATURE-----\niQGzBAEBCgAdFiEElrD5qQ78v1h4\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-2',
    title: 'Credit Card Dump (Valid)',
    category: 'Financial Services',
    price: 80,
    vendor: 'shadowmarket',
    rating: 4.7,
    ratingCount: 98,
    imageType: 'card',
    description: 'Synthetic Luhn-valid test track 1 & track 2 test data vectors. Ideal for payment processor stress tests and PCI-DSS compliance red team simulations.',
    specs: [
      { label: 'Track Format', value: 'ISO/IEC 7813 Track 1/2' },
      { label: 'BIN Range', value: '4111xx / 5500xx Test Sandbox' },
      { label: 'Validity Rate', value: '100% Synthetic Verified' },
      { label: 'Expiry Range', value: '2027 - 2029' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nBatch: SHDW-CARDS-9901-VAL\nSignature Verified by Escrow MultiSig\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-3',
    title: 'VPN Access (1 Year)',
    category: 'Access',
    price: 40,
    vendor: 'byteworks',
    rating: 4.6,
    ratingCount: 76,
    imageType: 'vpn',
    description: 'Offshore wireguard configuration profiles operating with RAM-only diskless nodes across Switzerland, Iceland, and Panama. No connection logging policy.',
    specs: [
      { label: 'Protocol', value: 'WireGuard / OpenVPN 256-bit' },
      { label: 'Bandwidth', value: '10 Gbps Unmetered Pipe' },
      { label: 'DNS Leak Protection', value: 'Autonomous Recursive Resolvers' },
      { label: 'Kill Switch', value: 'Hardware Layer Included' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nNode Cluster: OMEGA-SWISS-04\nByteworks Core Infrastructure Team\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-4',
    title: 'PGP Keys Collection',
    category: 'Digital Goods',
    price: 25,
    vendor: 'n1ghtjar_',
    rating: 4.9,
    ratingCount: 120,
    imageType: 'pgp',
    description: 'Curated 4096-bit RSA & Ed25519 public key directory and trust web mapping of historic underground market vendors and key escrow arbiters.',
    specs: [
      { label: 'Key Count', value: '4,500+ Verified Keys' },
      { label: 'Algorithm', value: 'RSA 4096 / Curve25519' },
      { label: 'Trust Database', value: 'GnuPG Keyring Export (.gpg)' },
      { label: 'Revocation Checks', value: 'Updated 2025.09' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nKeyring Digest: e982b6140ccba0\nVerified by n1ghtjar_ Authority\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-5',
    title: 'Malware Builder (FUD)',
    category: 'Malware & Tools',
    price: 120,
    vendor: 'voidseller',
    rating: 4.5,
    ratingCount: 65,
    imageType: 'malware',
    description: 'Demonstration payload compiler for educational malware reverse engineering labs. Compiles benign test indicators with polymorphic XOR obfuscation to study EDR heuristic detection.',
    specs: [
      { label: 'Obfuscation', value: 'Polymorphic Runtime XOR' },
      { label: 'Architecture', value: 'x86_64 / ARM64 PE & ELF' },
      { label: 'Payload Type', value: 'EICAR Heuristic Test Stub' },
      { label: 'EDR Test Matrix', value: 'Defender / CrowdStrike / SentinelOne' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nVoid-FUD Stub v3.1.4\nEducational Research Use Only\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-6',
    title: 'BTC to XMR Exchange',
    category: 'Financial Services',
    price: 60,
    vendor: 'cryptex',
    rating: 4.8,
    ratingCount: 54,
    imageType: 'crypto',
    description: 'Automated atomic swap simulation service. Zero-KYC non-custodial cross-chain cryptographic swaps with RingCT anonymity guarantee and stealth address emission.',
    specs: [
      { label: 'Swap Type', value: 'Cryptographic Atomic Swap' },
      { label: 'Fee Rate', value: '0.75% Flat Escrow Fee' },
      { label: 'Confirmations', value: '2 BTC / 10 XMR confirmations' },
      { label: 'Privacy Protocol', value: 'Bulletproofs+ & Ring Signatures' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nCryptex Liquidity Pool Alpha\nAutonomous Escrow Node 77\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-7',
    title: 'RDP Access (US/EU)',
    category: 'Access',
    price: 70,
    vendor: 'accesshub',
    rating: 4.6,
    ratingCount: 42,
    imageType: 'rdp',
    description: 'Dedicated high-speed remote desktop server instances with clean residential static IPs, NVMe flash storage, and administrator privileges for remote forensics staging.',
    specs: [
      { label: 'Hardware', value: '4 vCPU / 16 GB RAM / 256 GB NVMe' },
      { label: 'OS', value: 'Windows Server 2022 Datacenter' },
      { label: 'IP Type', value: 'Clean ISP Residential Fiber' },
      { label: 'Access Protocol', value: 'TLS 1.3 RDP on Port 3389' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nAccessHub Cluster EU-Frankfurt\nSession Token: AH-90412\n-----END PGP SIGNATURE-----'
  },
  {
    id: 'listing-8',
    title: 'Social Media Accounts',
    category: 'Digital Goods',
    price: 30,
    vendor: 'socialghost',
    rating: 4.4,
    ratingCount: 88,
    imageType: 'social',
    description: 'Aged social media honeypot accounts (Instagram, X, Reddit) with legacy creation dates (2018-2022) and verified email handles for OSINT sockpuppet research.',
    specs: [
      { label: 'Included Platforms', value: 'Instagram (2019), X (2020), Reddit (2018)' },
      { label: 'Followers / Karma', value: '500+ Natural Activity Score' },
      { label: 'Email Access', value: 'Original Mail (Proton/Tuta) included' },
      { label: '2FA Backup', value: 'TOTP Secret Seeds provided' }
    ],
    pgpSignature: '-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\nSocialGhost Batch SG-2025\nPGP Signature Validated\n-----END PGP SIGNATURE-----'
  }
];

export const RECENT_ITEMS: RecentItem[] = [
  {
    id: 'recent-1',
    title: 'UK Driving License (Scanned)',
    category: 'Documents',
    vendor: 'fakeidpro',
    price: 100,
    date: '2025-09-04',
    iconType: 'doc'
  },
  {
    id: 'recent-2',
    title: 'Instagram Followers (10k)',
    category: 'Digital Goods',
    vendor: 'socialghost',
    price: 25,
    date: '2025-09-04',
    iconType: 'social'
  },
  {
    id: 'recent-3',
    title: 'Corporate DB Access',
    category: 'Access',
    vendor: 'netrunner',
    price: 200,
    date: '2025-09-04',
    iconType: 'db'
  },
  {
    id: 'recent-4',
    title: 'X (Twitter) Accounts (Aged)',
    category: 'Digital Goods',
    vendor: 'socialghost',
    price: 40,
    date: '2025-09-03',
    iconType: 'x'
  }
];

export const TOP_VENDORS: Vendor[] = [
  {
    id: 'v1',
    handle: 'n1ghtjar_',
    emoji: '👑',
    rating: 4.9,
    deals: 120,
    category: 'Digital Goods',
    joined: '2023-01-15',
    pgpFingerprint: '9F42 E018 7AC3 881B 4501 EF78',
    reputationScore: 99.4
  },
  {
    id: 'v2',
    handle: 'shadowmarket',
    emoji: '🎭',
    rating: 4.8,
    deals: 98,
    category: 'Documents',
    joined: '2023-04-20',
    pgpFingerprint: '3C11 88A4 029F 1120 7B09 EE41',
    reputationScore: 98.1
  },
  {
    id: 'v3',
    handle: 'byteworks',
    emoji: '💀',
    rating: 4.7,
    deals: 76,
    category: 'Access',
    joined: '2023-08-11',
    pgpFingerprint: '77F2 CC19 901E 55A3 1899 D040',
    reputationScore: 96.9
  },
  {
    id: 'v4',
    handle: 'voidseller',
    emoji: '♠️',
    rating: 4.6,
    deals: 65,
    category: 'Malware & Tools',
    joined: '2023-11-02',
    pgpFingerprint: '110A FB42 3381 77EE 9182 AA05',
    reputationScore: 95.2
  },
  {
    id: 'v5',
    handle: 'cryptex',
    emoji: '⭐',
    rating: 4.5,
    deals: 54,
    category: 'Financial Services',
    joined: '2024-02-18',
    pgpFingerprint: '4E89 126B FA01 2293 8810 BC44',
    reputationScore: 94.7
  }
];

export const RELAYS_POOL = [
  { name: 'relay-01', ip: '185.220.101.5', country: 'Germany', countryCode: 'DE', latency: 48 },
  { name: 'relay-02', ip: '194.26.29.112', country: 'Netherlands', countryCode: 'NL', latency: 62 },
  { name: 'relay-03', ip: '185.100.86.199', country: 'Switzerland', countryCode: 'CH', latency: 54 },
  { name: 'relay-04', ip: '51.15.82.90', country: 'France', countryCode: 'FR', latency: 71 },
  { name: 'relay-05', ip: '109.70.100.24', country: 'Austria', countryCode: 'AT', latency: 65 },
  { name: 'relay-06', ip: '89.234.157.254', country: 'Iceland', countryCode: 'IS', latency: 89 },
  { name: 'relay-07', ip: '185.241.208.204', country: 'Sweden', countryCode: 'SE', latency: 58 }
];

export const FORUM_ALPHA_THREADS: ForumThread[] = [
  {
    id: 'thread-1',
    title: '[0-DAY LEAK] Arbitrary Kernel Memory Leak PoC (v6.1.x)',
    tag: '0-DAY',
    tagColor: 'text-red-400 bg-red-950/80 border-red-500/30',
    author: '0xNullPointer',
    replies: 14,
    views: 840,
    timeAgo: '2 hrs ago',
    excerpt: 'Demonstrating race condition in net/socket slab allocation allowing unprivileged user to dump adjacent kernel memory pages.',
    content: [
      'Disclosed for defensive patching simulation and SIEM detection signature development.',
      'Affected kernels: Linux 6.1.0 to 6.1.42 with unprivileged eBPF disabled.',
      'Exploit vector involves concurrent io_uring ring buffer reconfiguration during TCP socket handover.',
      'Mitigation: Apply upstream commit #d8f441b or set sysctl kernel.unprivileged_bpf_disabled=1.'
    ]
  },
  {
    id: 'thread-2',
    title: 'Analysis of recent automated wallet drainers circulating on Telegram',
    tag: 'INTEL',
    tagColor: 'text-amber-300 bg-amber-950/80 border-amber-500/30',
    author: 'cipher_warden',
    replies: 39,
    views: 1420,
    timeAgo: '5 hrs ago',
    excerpt: 'Decompilation of MS-WalletDrain v4 bot script targeting Solana & EVM browser extension popups via injected fake RPC nodes.',
    content: [
      'Threat actor group "VenomSpiders" deployed over 40 phishing domains masquerading as token airdrop claim contracts.',
      'Payload extracts encrypted localStorage session keys before triggering eth_signTransaction with blind parameters.',
      'Detection IOCs & Snort/Suricata rules attached for sandbox analysis.'
    ]
  },
  {
    id: 'thread-3',
    title: 'PGP Public Key Verification Best Practices 2025',
    tag: 'TUTORIAL',
    tagColor: 'text-cyan-300 bg-cyan-950/80 border-cyan-500/30',
    author: 'n1ghtjar_',
    replies: 62,
    views: 2980,
    timeAgo: '1 day ago',
    excerpt: 'Why fingerprint collision attacks mean you must never rely on the short 8-character Key-ID format.',
    content: [
      'Full 40-character hexadecimal fingerprints (or full V5 64-character SHA-256 digests) must be checked over out-of-band channels.',
      'Always sign vendor canary files and check revocation certificates against multiple decentralized key servers.',
      'Recommended GnuPG config: `keyid-format 0xlong` and `with-fingerprint` enabled by default.'
    ]
  },
  {
    id: 'thread-4',
    title: 'Tor v3 Hidden Service Denial-of-Service Countermeasures',
    tag: 'RESEARCH',
    tagColor: 'text-brand-accent bg-emerald-950/80 border-brand-accent/30',
    author: 'onion_architect',
    replies: 28,
    views: 1150,
    timeAgo: '2 days ago',
    excerpt: 'Implementing PoW (Proof-of-Work) Equi-X algorithms in introductory circuit cells to defeat bot rendezvous flooding.',
    content: [
      'Tor 0.4.8.x introduced PoW defenses against intro cell flooding.',
      'Benchmark results indicate 99.2% CPU exhaustion reduction on onion hidden services under synthetic 10k conn/sec test traffic.'
    ]
  }
];
