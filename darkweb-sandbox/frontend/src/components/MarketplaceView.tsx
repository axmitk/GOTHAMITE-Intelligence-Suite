import React, { useState, useMemo, useEffect } from 'react';
import {
  Search,
  ChevronRight,
  Shield,
  Layers,
  FileText,
  Clock,
  ExternalLink,
  Info,
  CheckCircle2,
  X,
  User
} from 'lucide-react';
import { ListingItem, RecentItem, Vendor, MarketplaceTab } from '../types';
import { RECENT_ITEMS, TOP_VENDORS } from '../data/mockData';
import { ListingGraphic } from './ListingGraphic';
import { fetchSandboxPage, parseIndexPage, parseItemPage } from '../services/sandboxGateway';

interface MarketplaceViewProps {
  onOpenListing: (item: ListingItem) => void;
  onOpenAuth: (mode: 'login' | 'register') => void;
  currentUser: string | null;
  onLogout: () => void;
}

export const MarketplaceView: React.FC<MarketplaceViewProps> = ({
  onOpenListing,
  onOpenAuth,
  currentUser,
  onLogout
}) => {
  const [activeTab, setActiveTab] = useState<MarketplaceTab>('listings');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedVendor, setSelectedVendor] = useState<string | null>(null);
  const [listings, setListings] = useState<ListingItem[]>([]);
  const [loading, setLoading] = useState(true);

  const categories = [
    'Digital Goods',
    'Access',
    'Financial Services',
    'Documents',
    'Malware & Tools',
    'Other (All Items)'
  ];

  useEffect(() => {
    const loadListings = async () => {
      try {
        const { html } = await fetchSandboxPage('beta4np8vz3wc.onion.mock/');
        const { items } = parseIndexPage(html);
        
        const mappedListings: ListingItem[] = items.map((item: any, idx: number) => ({
          id: item.id,
          title: item.title,
          category: 'Other', 
          price: 100, // synthetic placeholder
          vendor: item.author,
          rating: 4.8,
          ratingCount: 10,
          imageType: 'doc',
          description: `Sandbox Item: ${item.title}`,
          specs: [],
          pgpSignature: '',
          rawHref: item.id
        } as any));
        
        setListings(mappedListings);
      } catch (err) {
        console.error("Error loading Marketplace:", err);
      } finally {
        setLoading(false);
      }
    };
    loadListings();
  }, []);

  // Filter listings based on category, vendor, and search query
  const filteredListings = useMemo(() => {
    return listings.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.vendor.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        !selectedCategory ||
        selectedCategory === 'Other (All Items)' ||
        item.category === selectedCategory ||
        selectedCategory === 'Other';

      const matchesVendor = !selectedVendor || item.vendor === selectedVendor;

      return matchesSearch && matchesCategory && matchesVendor;
    });
  }, [searchQuery, selectedCategory, selectedVendor, listings]);

  // Filter recent items
  const filteredRecentItems = useMemo(() => {
    return RECENT_ITEMS.filter((item) => {
      const matchesSearch =
        !searchQuery ||
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.vendor.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.category.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesCategory =
        !selectedCategory ||
        selectedCategory === 'Other (All Items)' ||
        item.category === selectedCategory;

      const matchesVendor = !selectedVendor || item.vendor === selectedVendor;

      return matchesSearch && matchesCategory && matchesVendor;
    });
  }, [searchQuery, selectedCategory, selectedVendor]);

  const handleCategoryClick = (cat: string) => {
    if (cat === 'Other (All Items)') {
      setSelectedCategory(null);
    } else {
      setSelectedCategory(selectedCategory === cat ? null : cat);
    }
  };

  const handleVendorClick = (vendorHandle: string) => {
    setSelectedVendor(selectedVendor === vendorHandle ? null : vendorHandle);
  };

  const clearFilters = () => {
    setSelectedCategory(null);
    setSelectedVendor(null);
    setSearchQuery('');
  };

  // Helper to convert RecentItem into a displayable ListingItem for modal
  const handleRecentItemClick = (recent: RecentItem) => {
    const matched = listings.find((l) => l.title === recent.title);
    if (matched) {
      onOpenListing(matched);
    } else {
      onOpenListing({
        id: recent.id,
        title: recent.title,
        category: recent.category as any,
        price: recent.price,
        vendor: recent.vendor,
        rating: 4.7,
        ratingCount: 52,
        imageType: 'doc',
        description: `Synthetic verified record for "${recent.title}". Verified through simulated escrow protocol.`,
        specs: [
          { label: 'Category', value: recent.category },
          { label: 'Added Date', value: recent.date },
          { label: 'Vendor Status', value: 'Verified Tier-2' }
        ],
        pgpSignature: `-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\nTitle: ${recent.title}\nVendor: ${recent.vendor}\n-----END PGP SIGNATURE-----`
      });
    }
  };

  return (
    <div id="view-marketplace" className="p-4 md:p-6 space-y-5 max-w-7xl mx-auto">
      {/* Marketplace Top Header */}
      <div
        id="marketplace-header"
        className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#153634] pb-4"
      >
        {/* Brand Identity */}
        <div className="flex items-center space-x-3.5">
          {/* Skull Avatar */}
          <div className="w-12 h-12 rounded bg-black/70 border border-[#1d4a46] flex items-center justify-center p-1.5 shadow-inner">
            <svg className="w-9 h-9 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                d="M12 2a8 8 0 0 0-8 8c0 3.2 1.8 5.8 4 7.2V20a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.8c2.2-1.4 4-4 4-7.2a8 8 0 0 0-8-8z"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="1.6"
              />
              <circle cx="9" cy="11" fill="currentColor" r="1.5" />
              <circle cx="15" cy="11" fill="currentColor" r="1.5" />
              <path d="M9 17v3M12 17v3M15 17v3" strokeLinecap="round" strokeWidth="1.6" />
            </svg>
          </div>
          <div>
            <div className="flex items-baseline space-x-2">
              <h2 className="text-xl md:text-2xl font-bold font-mono tracking-widest text-[#2bf0a6]">
                DarkTrade
              </h2>
              <span className="text-[10px] font-mono uppercase bg-emerald-950/80 text-[#2bf0a6] px-1.5 py-0.5 rounded border border-[#2bf0a6]/30 font-semibold tracking-wider">
                MARKETPLACE BETA
              </span>
            </div>
            <p className="text-xs font-mono text-gray-400 mt-0.5">anonymous trade. real freedom.</p>
          </div>
        </div>

        {/* Login / Auth & Search Bar */}
        <div className="flex flex-col items-end space-y-2">
          <div className="text-xs font-mono space-x-2 text-gray-400 flex items-center">
            {currentUser ? (
              <>
                <span className="text-[#2bf0a6] flex items-center gap-1 font-medium">
                  <User className="w-3.5 h-3.5" /> @{currentUser}
                </span>
                <span>|</span>
                <button
                  onClick={onLogout}
                  className="hover:text-red-400 text-gray-400 transition cursor-pointer"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => onOpenAuth('login')}
                  className="hover:text-[#2bf0a6] transition cursor-pointer"
                >
                  Login
                </button>
                <span>|</span>
                <button
                  onClick={() => onOpenAuth('register')}
                  className="hover:text-[#2bf0a6] transition cursor-pointer"
                >
                  Register
                </button>
              </>
            )}
          </div>

          <div className="flex items-center space-x-1.5 w-full md:w-80">
            <div className="relative flex-1">
              <input
                id="marketplace-search-input"
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search listings..."
                className="w-full bg-[#040c0d] border border-[#1d4a46] text-gray-200 text-xs rounded px-3 py-1.5 focus:outline-none focus:border-[#2bf0a6] placeholder-gray-500 font-mono tracking-wide"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <button
              id="marketplace-search-btn"
              onClick={() => {}}
              className="bg-gradient-to-r from-[#175249] to-[#0c3933] hover:from-[#1d6b5f] hover:to-[#0f4941] text-[#2bf0a6] border border-[#2bf0a6]/40 text-xs font-mono font-medium px-4 py-1.5 rounded transition shadow-xs cursor-pointer"
            >
              Search
            </button>
          </div>
        </div>
      </div>

      {/* Secondary Tabs Strip */}
      <div className="flex space-x-2 border-b border-[#153634]/70 pb-2 text-xs font-mono">
        <button
          onClick={() => setActiveTab('home')}
          className={`px-3.5 py-1 rounded transition cursor-pointer ${
            activeTab === 'home'
              ? 'text-[#2bf0a6] bg-[#112929] border border-[#2bf0a6]/40 font-medium'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Home
        </button>
        <button
          onClick={() => setActiveTab('listings')}
          className={`px-3.5 py-1 rounded transition cursor-pointer ${
            activeTab === 'listings'
              ? 'text-[#2bf0a6] bg-[#112929] border border-[#2bf0a6]/40 font-medium'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Listings
        </button>
        <button
          onClick={() => setActiveTab('vendors')}
          className={`px-3.5 py-1 rounded transition cursor-pointer ${
            activeTab === 'vendors'
              ? 'text-[#2bf0a6] bg-[#112929] border border-[#2bf0a6]/40 font-medium'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Vendors
        </button>
        <button
          onClick={() => setActiveTab('escrow')}
          className={`px-3.5 py-1 rounded transition cursor-pointer ${
            activeTab === 'escrow'
              ? 'text-[#2bf0a6] bg-[#112929] border border-[#2bf0a6]/40 font-medium'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Escrow
        </button>
        <button
          onClick={() => setActiveTab('help')}
          className={`px-3.5 py-1 rounded transition cursor-pointer ${
            activeTab === 'help'
              ? 'text-[#2bf0a6] bg-[#112929] border border-[#2bf0a6]/40 font-medium'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Help
        </button>
      </div>

      {/* Tab Specific Content */}
      {activeTab === 'vendors' && (
        <div className="p-4 bg-[#0d1f20] border border-[#153634] rounded-lg font-mono space-y-4">
          <div className="flex items-center justify-between border-b border-[#153634] pb-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Verified Marketplace Vendors Directory
            </h3>
            <span className="text-xs text-[#2bf0a6] bg-emerald-950 px-2 py-0.5 rounded border border-[#2bf0a6]/30">
              PGP Web-of-Trust Active
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {TOP_VENDORS.map((vendor) => (
              <div
                key={vendor.id}
                className="p-3 bg-[#061113] border border-[#153634] rounded space-y-2 hover:border-[#2bf0a6]/50 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{vendor.emoji}</span>
                    <div>
                      <div className="text-xs font-bold text-gray-200">@{vendor.handle}</div>
                      <div className="text-[10px] text-gray-400">{vendor.category}</div>
                    </div>
                  </div>
                  <div className="text-right text-xs">
                    <span className="text-amber-400">★ {vendor.rating}</span>
                    <div className="text-[9px] text-gray-500">({vendor.deals} deals)</div>
                  </div>
                </div>
                <div className="text-[9px] text-gray-400 bg-black/40 p-1.5 rounded font-mono truncate">
                  Key: {vendor.pgpFingerprint}
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-[#2bf0a6]">Rep: {vendor.reputationScore}%</span>
                  <button
                    onClick={() => {
                      setSelectedVendor(vendor.handle);
                      setActiveTab('listings');
                    }}
                    className="text-[10px] text-[#2bf0a6] hover:underline"
                  >
                    View Listings →
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'escrow' && (
        <div className="p-4 bg-[#0d1f20] border border-[#153634] rounded-lg font-mono space-y-4">
          <div className="border-b border-[#153634] pb-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Autonomous Multi-Signature Escrow Protocol
            </h3>
            <p className="text-xs text-gray-400">
              Zero-trust financial dispute resolution model architecture
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-[#061113] border border-[#153634] rounded space-y-1.5">
              <span className="text-[#2bf0a6] font-bold">1. Order Staging</span>
              <p className="text-gray-400 text-[11px]">
                Buyer locks funds in a 2-of-3 multisig script requiring keys from Buyer, Vendor, and Marketplace Arbiter.
              </p>
            </div>
            <div className="p-3 bg-[#061113] border border-[#153634] rounded space-y-1.5">
              <span className="text-[#2bf0a6] font-bold">2. Encrypted Dispatch</span>
              <p className="text-gray-400 text-[11px]">
                Vendor releases PGP encrypted tracking or digital key payload over simulated onion network circuits.
              </p>
            </div>
            <div className="p-3 bg-[#061113] border border-[#153634] rounded space-y-1.5">
              <span className="text-[#2bf0a6] font-bold">3. Timelock Release</span>
              <p className="text-gray-400 text-[11px]">
                Upon successful receipt verification, Buyer signs transaction; funds auto-release to Vendor address.
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'help' && (
        <div className="p-4 bg-[#0d1f20] border border-[#153634] rounded-lg font-mono space-y-3 text-xs">
          <div className="border-b border-[#153634] pb-2">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              DarkTrade Sandbox Knowledgebase &amp; FAQs
            </h3>
            <p className="text-[11px] text-gray-400">Threat research guide and protocol documentation</p>
          </div>
          <div className="space-y-2">
            <div className="p-2.5 bg-[#061113] rounded border border-[#153634]">
              <div className="font-bold text-[#2bf0a6] mb-1">Q: How does this sandbox handle payments?</div>
              <p className="text-gray-400 text-[11px]">
                All BTC, XMR, and USD amounts shown are simulated test currency designed strictly for educational UI audits.
              </p>
            </div>
            <div className="p-2.5 bg-[#061113] rounded border border-[#153634]">
              <div className="font-bold text-[#2bf0a6] mb-1">Q: What is the "New Identity" button?</div>
              <p className="text-gray-400 text-[11px]">
                It simulates sending a `NEWNYM` control command to the local Tor daemon, building an entirely new circuit of 3 relays.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Hero Banner Section */}
      {(activeTab === 'listings' || activeTab === 'home') && (
        <div
          id="hero-banner"
          className="relative rounded-lg overflow-hidden border border-[#153634] bg-gradient-to-r from-[#071719] via-[#092223] to-[#051112] min-h-[160px] flex items-center px-6 py-5 shadow-lg"
        >
          {/* Digital matrix / Silhouette overlay visual */}
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(43,240,166,0.06),transparent_70%)] pointer-events-none" />

          {/* Left Category Link List */}
          <div className="w-full md:w-1/3 z-10 space-y-1 text-xs font-mono border-r border-[#153634]/60 pr-4">
            {categories.map((category) => {
              const isActive =
                selectedCategory === category ||
                (category === 'Other (All Items)' && selectedCategory === null);

              return (
                <button
                  key={category}
                  onClick={() => handleCategoryClick(category)}
                  className={`category-filter-btn flex items-center justify-between w-full py-0.5 text-left transition cursor-pointer ${
                    isActive
                      ? 'text-[#2bf0a6] font-semibold pl-1'
                      : 'text-gray-300 hover:text-[#2bf0a6]'
                  }`}
                >
                  <span>{category}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-500" />
                </button>
              );
            })}
          </div>

          {/* Hooded Silhouette & Manifesto Typography */}
          <div className="hidden md:flex flex-1 items-center justify-center relative pl-8 select-none">
            {/* Center Hooded Avatar graphic */}
            <div className="relative w-36 h-36 flex items-center justify-center shrink-0 opacity-80">
              <svg className="w-32 h-32 text-[#0f3b37]" fill="currentColor" viewBox="0 0 100 100">
                <path d="M50 8C33 8 20 22 20 40c0 14 6 22 10 32 3 7 4 18 4 20h32s1-13 4-20c4-10 10-18 10-32 0-18-13-32-30-32z" />
                {/* Faceless shadow inset */}
                <path
                  d="M50 25c-10 0-18 10-18 24 0 12 6 20 18 20s18-8 18-20c0-14-8-24-18-24z"
                  fill="#04090a"
                />
              </svg>
            </div>

            {/* Right Quote Typography */}
            <div className="ml-6 space-y-2">
              <h3 className="text-lg lg:text-xl font-bold font-mono tracking-wider text-[#2bf0a6] uppercase leading-tight">
                PRIVACY IS A RIGHT,
                <br />
                NOT A CRIME.
              </h3>
              <p className="text-xs font-serif italic text-gray-400 tracking-wide">— DarkTrade</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Listings (Left 75%) + Right Sidebars (Right 25%) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 items-start">
        {/* Left 3 Columns: Featured Listings Grid + Recent Table */}
        <div className="lg:col-span-3 space-y-6">
          {/* Featured Listings Header & Active Filters */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <h3 className="text-sm font-semibold font-mono text-gray-200 tracking-wide">
                Featured Listings
              </h3>
              <span className="text-xs text-gray-500 font-mono">
                ({filteredListings.length} {filteredListings.length === 1 ? 'item' : 'items'})
              </span>
            </div>

            {(selectedCategory || selectedVendor || searchQuery) && (
              <div className="flex items-center space-x-2">
                <span
                  id="active-filter-badge"
                  className="text-[11px] font-mono text-[#2bf0a6] bg-[#0e332e] px-2 py-0.5 rounded border border-[#2bf0a6]/30 flex items-center gap-1.5"
                >
                  <span>
                    Filtering:{' '}
                    <span id="filter-name" className="font-semibold text-white">
                      {selectedCategory || (selectedVendor ? `@${selectedVendor}` : `"${searchQuery}"`)}
                    </span>
                  </span>
                  <button
                    onClick={clearFilters}
                    className="hover:text-red-400 text-gray-400 ml-1 cursor-pointer"
                    title="Clear filter"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              </div>
            )}
          </div>

          {/* 8 Cards Grid (4 cols on desktop x 2 rows) */}
          <div
            id="listings-grid"
            className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3.5"
          >
            {filteredListings.length > 0 ? (
              filteredListings.map((item) => (
                <div
                  key={item.id}
                  className="listing-card bg-[#0d1f20] border border-[#153634] rounded p-2.5 flex flex-col justify-between hover:border-[#2bf0a6]/60 transition group shadow-sm hover:shadow-[0_0_15px_rgba(43,240,166,0.1)]"
                >
                  <div className="h-28 bg-[#061113] rounded border border-[#153634]/50 overflow-hidden relative flex items-center justify-center">
                    <ListingGraphic type={item.imageType} />
                  </div>

                  <div className="mt-2 space-y-1">
                    <h4
                      onClick={() => onOpenListing(item)}
                      className="text-xs font-semibold text-gray-200 truncate group-hover:text-[#2bf0a6] cursor-pointer"
                      title={item.title}
                    >
                      {item.title}
                    </h4>
                    <div className="text-[10px] text-gray-400 font-mono">{item.category}</div>
                    <div className="flex items-center text-[10px] font-mono text-gray-400 space-x-1">
                      <span className="text-amber-400">★ {item.rating}</span>
                      <span>|</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleVendorClick(item.vendor);
                        }}
                        className="text-gray-400 hover:text-[#2bf0a6] truncate cursor-pointer"
                      >
                        {item.vendor}
                      </button>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-xs font-bold text-[#2bf0a6] font-mono">
                        ${item.price}
                      </span>
                      <button
                        onClick={() => onOpenListing(item)}
                        className="btn-open-listing bg-[#0e332e] hover:bg-[#2bf0a6] hover:text-black text-[#2bf0a6] border border-[#2bf0a6]/40 text-[11px] font-mono px-3 py-0.5 rounded transition cursor-pointer font-medium"
                      >
                        View
                      </button>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full py-8 text-center text-xs font-mono text-gray-500 bg-[#061113] border border-[#153634] rounded">
                No listings found matching the active filter criteria.{' '}
                <button onClick={clearFilters} className="text-[#2bf0a6] underline ml-1 cursor-pointer">
                  Reset filters
                </button>
              </div>
            )}
          </div>

          {/* Recently Added Table Section */}
          <div id="recently-added-section" className="pt-3">
            <div className="flex items-center justify-between mb-2.5">
              <h3 className="text-sm font-semibold font-mono text-gray-200 tracking-wide">
                Recently Added
              </h3>
              <button
                onClick={() => {
                  setSelectedCategory(null);
                  setSelectedVendor(null);
                  setSearchQuery('');
                }}
                className="text-xs font-mono text-[#2bf0a6] hover:underline flex items-center space-x-1 cursor-pointer"
              >
                <span>View All</span>
                <span>→</span>
              </button>
            </div>

            <div className="border border-[#153634] rounded overflow-hidden bg-[#0d1f20]">
              <table className="w-full text-left text-xs font-mono border-collapse" id="recently-added-table">
                <thead>
                  <tr className="border-b border-[#153634] bg-[#0a1819] text-gray-400">
                    <th className="py-2 px-3 font-medium">Title</th>
                    <th className="py-2 px-3 font-medium">Category</th>
                    <th className="py-2 px-3 font-medium">Vendor</th>
                    <th className="py-2 px-3 font-medium">Price</th>
                    <th className="py-2 px-3 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#153634]/60 text-gray-300">
                  {filteredRecentItems.map((recent) => (
                    <tr
                      key={recent.id}
                      onClick={() => handleRecentItemClick(recent)}
                      className="recent-row hover:bg-[#112929]/70 transition cursor-pointer"
                    >
                      <td className="py-2 px-3 flex items-center space-x-2">
                        <FileText className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                        <span className="truncate">{recent.title}</span>
                      </td>
                      <td className="py-2 px-3 text-gray-400">{recent.category}</td>
                      <td className="py-2 px-3 text-gray-400">{recent.vendor}</td>
                      <td className="py-2 px-3 text-[#2bf0a6] font-semibold">${recent.price}</td>
                      <td className="py-2 px-3 text-gray-400">{recent.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right 1 Column: Top Vendors & Stats Panels */}
        <div id="marketplace-right-sidebar" className="space-y-4">
          {/* Top Vendors Card */}
          <div className="bg-[#0d1f20] border border-[#153634] rounded p-3 font-mono space-y-3">
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider pb-1.5 border-b border-[#153634]/70">
              Top Vendors
            </h4>
            <div className="space-y-2.5">
              {TOP_VENDORS.map((vendor) => {
                const isSelected = selectedVendor === vendor.handle;
                return (
                  <div
                    key={vendor.id}
                    onClick={() => handleVendorClick(vendor.handle)}
                    className={`flex items-center space-x-2.5 group cursor-pointer p-1 rounded transition ${
                      isSelected ? 'bg-[#112929] border border-[#2bf0a6]/40' : 'hover:bg-[#112929]/50'
                    }`}
                  >
                    <span className="text-sm shrink-0">{vendor.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between text-xs">
                        <span
                          className={`font-medium truncate ${
                            isSelected ? 'text-[#2bf0a6]' : 'text-gray-200 group-hover:text-[#2bf0a6]'
                          }`}
                        >
                          {vendor.handle}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-gray-400">
                        <span className="text-amber-400">
                          ★ {vendor.rating}{' '}
                          <span className="text-gray-500">({vendor.deals})</span>
                        </span>
                        <span className="text-gray-500 truncate">{vendor.category}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Marketplace Stats Card */}
          <div className="bg-[#0d1f20] border border-[#153634] rounded p-3 font-mono space-y-2.5">
            <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider pb-1.5 border-b border-[#153634]/70">
              Marketplace Stats
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-400">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Total Listings</span>
                </div>
                <span id="stat-listings-count" className="text-gray-200 font-semibold">
                  1,248
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-400">
                  <User className="w-3.5 h-3.5" />
                  <span>Active Vendors</span>
                </div>
                <span className="text-gray-200 font-semibold">312</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-400">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Successful Trades</span>
                </div>
                <span className="text-gray-200 font-semibold">4,921</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-400">
                  <Shield className="w-3.5 h-3.5" />
                  <span>Escrow Protected</span>
                </div>
                <span className="text-[#2bf0a6] font-semibold">Yes</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-gray-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Uptime</span>
                </div>
                <span className="text-[#2bf0a6] font-semibold">99.7%</span>
              </div>
            </div>
          </div>

          {/* Philosophical Quote Card */}
          <div className="border border-[#153634]/70 rounded p-3.5 bg-gradient-to-br from-[#061416] to-[#040c0d] text-center">
            <p className="font-serif italic text-xs text-gray-400">
              "Trust the network,
              <br />
              not the people."
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
