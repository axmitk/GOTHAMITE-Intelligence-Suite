import React, { useState, useCallback } from 'react';
import { TitleBar } from './components/TitleBar';
import { NavigationBar } from './components/NavigationBar';
import { Sidebar } from './components/Sidebar';
import { MarketplaceView } from './components/MarketplaceView';
import { ForumAlphaView } from './components/ForumAlphaView';
import { ForumGammaView } from './components/ForumGammaView';
import { HomeView } from './components/HomeView';
import { ListingModal } from './components/ListingModal';
import { CircuitModal } from './components/CircuitModal';
import { AuthModal } from './components/AuthModal';
import { NavView, CircuitHop, ListingItem } from './types';
import { RELAYS_POOL } from './data/mockData';

const VIEW_URLS: Record<NavView, string> = {
  marketplace: 'http://marketplace-beta.onion.mock/',
  'forum-alpha': 'http://forum-alpha.onion.mock/',
  'forum-gamma': 'http://forum-gamma.onion.mock/',
  home: 'http://sandbox-home.onion.mock/'
};

export default function App() {
  // Navigation State
  const [currentView, setCurrentView] = useState<NavView>('marketplace');
  const [history, setHistory] = useState<NavView[]>(['marketplace']);
  const [historyIndex, setHistoryIndex] = useState<number>(0);

  // Circuit Route State
  const [realRelayPath, setRealRelayPath] = useState('Route unavailable');
  const [routeFlicker, setRouteFlicker] = useState(false);
  const [isGeneratingIdentity, setIsGeneratingIdentity] = useState(false);

  React.useEffect(() => {
    import('./services/sandboxGateway').then(gw => {
      const unsub = gw.onPathChange((newPath) => {
        setRealRelayPath(newPath);
        setRouteFlicker(true);
        setTimeout(() => setRouteFlicker(false), 500);
      });
      return unsub;
    });
  }, []);

  const dummyCircuit: CircuitHop[] = realRelayPath !== 'Route unavailable' && realRelayPath.includes('->')
    ? realRelayPath.split('->').map(r => r.trim()).map((r, idx) => ({
        name: r,
        ip: 'unknown',
        country: 'unknown',
        countryCode: 'XX',
        role: idx === 0 ? 'guard' : idx === 1 ? 'middle' : 'exit',
        latency: 0
      }))
    : [
        { name: realRelayPath, ip: 'unknown', country: 'unknown', countryCode: 'XX', role: 'middle', latency: 0 }
      ];

  // Modals State
  const [selectedListing, setSelectedListing] = useState<ListingItem | null>(null);
  const [isCircuitModalOpen, setIsCircuitModalOpen] = useState(false);
  const [authModal, setAuthModal] = useState<{ isOpen: boolean; mode: 'login' | 'register' }>({
    isOpen: false,
    mode: 'login'
  });
  const [currentUser, setCurrentUser] = useState<string | null>(null);

  // Navigation Handlers
  const handleSelectView = useCallback(
    (view: NavView) => {
      if (view === currentView) return;
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push(view);
      setHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
      setCurrentView(view);
    },
    [currentView, history, historyIndex]
  );

  const handleBack = useCallback(() => {
    if (historyIndex > 0) {
      const prevIndex = historyIndex - 1;
      setHistoryIndex(prevIndex);
      setCurrentView(history[prevIndex]);
    }
  }, [historyIndex, history]);

  const handleForward = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextIndex = historyIndex + 1;
      setHistoryIndex(nextIndex);
      setCurrentView(history[nextIndex]);
    }
  }, [historyIndex, history]);

  const handleNavigateUrl = useCallback(
    (url: string) => {
      const lower = url.toLowerCase();
      if (lower.includes('alpha')) {
        handleSelectView('forum-alpha');
      } else if (lower.includes('gamma')) {
        handleSelectView('forum-gamma');
      } else if (lower.includes('home') || lower.includes('sandbox')) {
        handleSelectView('home');
      } else {
        handleSelectView('marketplace');
      }
    },
    [handleSelectView]
  );

  // New Identity Generator
  const handleNewIdentity = useCallback(() => {
    // Cannot force new identity externally without breaking isolation.
    // The demo_viewer auto-rotates anyway.
  }, []);

  return (
    <div className="bg-[#030708] text-gray-200 font-sans min-h-screen select-none overflow-x-hidden flex flex-col items-center justify-center p-0 md:p-3">
      {/* Application Window Frame */}
      <div
        id="desktop-app-wrapper"
        className="w-full max-w-[1600px] h-screen md:h-[960px] bg-[#0a1617] border border-[#153634] md:rounded-lg shadow-2xl flex flex-col overflow-hidden relative"
      >
        {/* Top OS / Browser Window Titlebar */}
        <TitleBar
          onMinimize={() => {}}
          onMaximize={() => {}}
          onClose={() => {}}
        />

        {/* Top Browser Navigation Bar (URL + Circuit Indicator) */}
        <NavigationBar
          currentUrl={VIEW_URLS[currentView]}
          onNavigateUrl={handleNavigateUrl}
          canGoBack={historyIndex > 0}
          canGoForward={historyIndex < history.length - 1}
          onBack={handleBack}
          onForward={handleForward}
          circuitRoute={dummyCircuit}
          onOpenCircuitModal={() => setIsCircuitModalOpen(true)}
          routeFlicker={routeFlicker}
        />

        {/* Window Body (Sidebar + Viewport Content) */}
        <div id="main-layout-container" className="flex flex-1 overflow-hidden">
          {/* Left Sidebar */}
          <Sidebar
            currentView={currentView}
            onSelectView={handleSelectView}
            onNewIdentity={handleNewIdentity}
            isGeneratingIdentity={isGeneratingIdentity}
          />

          {/* Main Viewport */}
          <main
            id="sandbox-viewport"
            className="flex-1 bg-[#071314] overflow-y-auto cyber-grid-pattern relative"
          >
            {currentView === 'marketplace' && (
              <MarketplaceView
                onOpenListing={(item) => setSelectedListing(item)}
                onOpenAuth={(mode) => setAuthModal({ isOpen: true, mode })}
                currentUser={currentUser}
                onLogout={() => setCurrentUser(null)}
              />
            )}

            {currentView === 'forum-alpha' && <ForumAlphaView />}

            {currentView === 'forum-gamma' && <ForumGammaView />}

            {currentView === 'home' && <HomeView onSelectView={handleSelectView} />}
          </main>
        </div>

        {/* Modals */}
        <ListingModal
          listing={selectedListing}
          onClose={() => setSelectedListing(null)}
        />

        <CircuitModal
          isOpen={isCircuitModalOpen}
          onClose={() => setIsCircuitModalOpen(false)}
          circuitRoute={dummyCircuit}
          onNewIdentity={handleNewIdentity}
          isGeneratingIdentity={isGeneratingIdentity}
        />

        <AuthModal
          isOpen={authModal.isOpen}
          mode={authModal.mode}
          onClose={() => setAuthModal({ isOpen: false, mode: 'login' })}
          onSuccess={(username) => setCurrentUser(username)}
        />
      </div>
    </div>
  );
}
