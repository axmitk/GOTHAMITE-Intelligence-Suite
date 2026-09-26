export type NavView = 'marketplace' | 'forum-alpha' | 'forum-gamma' | 'home';

export type MarketplaceTab = 'home' | 'listings' | 'vendors' | 'escrow' | 'help';

export interface ListingItem {
  id: string;
  title: string;
  category: 'Documents' | 'Financial Services' | 'Access' | 'Digital Goods' | 'Malware & Tools' | 'Other';
  price: number;
  vendor: string;
  rating: number;
  ratingCount: number;
  imageType: 'passport' | 'card' | 'vpn' | 'pgp' | 'malware' | 'crypto' | 'rdp' | 'social';
  description: string;
  specs?: { label: string; value: string }[];
  pgpSignature: string;
}

export interface RecentItem {
  id: string;
  title: string;
  category: string;
  vendor: string;
  price: number;
  date: string;
  iconType: 'doc' | 'social' | 'db' | 'x';
}

export interface Vendor {
  id: string;
  handle: string;
  emoji: string;
  rating: number;
  deals: number;
  category: string;
  joined: string;
  pgpFingerprint: string;
  reputationScore: number;
}

export interface CircuitHop {
  name: string;
  ip: string;
  country: string;
  countryCode: string;
  role: 'guard' | 'middle' | 'exit';
  latency: number;
}

export interface ForumThread {
  id: string;
  title: string;
  tag: 'RESEARCH' | 'INTEL' | 'TUTORIAL' | 'EXPLOIT' | '0-DAY';
  tagColor: string;
  author: string;
  replies: number;
  views: number;
  timeAgo: string;
  excerpt: string;
  content: string[];
}
