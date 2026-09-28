import { Component, lazy, Suspense, useEffect, useRef, useState } from "react";
import type { ErrorInfo, ReactNode } from "react";
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  FolderOpen,
  Users,
  Server,
  Radar,
  ShieldCheck,
  FileText,
  Network,
  ArrowUpRight,
  X,
  Menu,
} from "lucide-react";
import { CommandCenter } from "./CommandCenter";
import { Badge, Heading, ResourceState } from "./ui";
import "./workbench.css";

const Intelligence = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.Intelligence })),
);
const EntityProfile = lazy(() =>
  import("./Intelligence").then((m) => ({ default: m.EntityProfile })),
);
const Investigation = lazy(() =>
  import("./Investigation").then((m) => ({ default: m.Investigation })),
);
const Reports = lazy(() =>
  import("./Investigation").then((m) => ({ default: m.Reports })),
);
const NistOverview = lazy(() =>
  import("./Investigation").then((m) => ({ default: m.NistOverview })),
);
const LegacyOverview = lazy(() =>
  import("../pages/Overview").then((m) => ({ default: m.Overview })),
);
const LegacyGraph = lazy(() =>
  import("../pages/Graph").then((m) => ({ default: m.Graph })),
);
const LegacyDossier = lazy(() =>
  import("../pages/Dossier").then((m) => ({ default: m.Dossier })),
);
const LegacyTimeline = lazy(() =>
  import("../pages/Timeline").then((m) => ({ default: m.Timeline })),
);

class WorkbenchBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(
      "Workbench render failed",
      error.message,
      info.componentStack,
    );
  }
  render() {
    return this.state.error ? (
      <div className="wb-resource">
        <h1>The workbench could not render this view.</h1>
        <p>Your saved case data remains in the database.</p>
        <button
          className="wb-button"
          onClick={() => window.location.assign("/command")}
        >
          Return to command center
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}

function DemoGuide({ onClose }: { onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="wb-guide"
      onCancel={onClose}
      aria-labelledby="guide-title"
    >
      <div className="wb-spread">
        <span className="wb-eyebrow">GOTHAMITE / FIELD GUIDE</span>
        <button
          className="wb-icon-button"
          aria-label="Close demo guide"
          onClick={onClose}
        >
          <X size={18} />
        </button>
      </div>
      <h2 id="guide-title">Trace the investigation.</h2>
      <p>
        Every item in this exercise is synthetic. The analysis uses transparent
        evidence rules, and all response actions are simulated.
      </p>
      <ol>
        <li>
          Search <code>203.0.113.42</code> in global search.
        </li>
        <li>Inspect its profile, enrichment and supporting observations.</li>
        <li>
          Explore the graph and open <code>INC-1042</code>.
        </li>
        <li>Review Analysis, the risk factors and NIST alignment.</li>
        <li>Add a hypothesis in the analyst notebook.</li>
        <li>In Response, approve a recommendation, then run its simulation.</li>
        <li>Advance the case and export the investigation report.</li>
      </ol>
      <p>
        Closure requires a recovery validation entry, a lesson learned, and a
        simulated recovery action.
      </p>
      <Link
        to="/intelligence?q=203.0.113.42"
        className="wb-button primary"
        onClick={onClose}
      >
        Inspect 203.0.113.42 <ArrowUpRight size={15} />
      </Link>
    </dialog>
  );
}

function ToolkitFrame({ children }: { children: ReactNode }) {
  return (
    <div className="wb-toolkit">
      <Heading
        eyebrow="Existing toolkit / integrated capability"
        title="Persona correlation"
        subtitle="Cross-source persona correlation over synthetic source artifacts. Scores are confidence-weighted identity associations, not incident risk."
      >
        <Badge value="Synthetic fixtures" tone="demo" />
        <Link className="wb-button quiet" to="/investigations">
          Return to investigations
        </Link>
      </Heading>
      <div
        className="wb-pipeline wb-toolkit-pipeline"
        aria-label="Correlation pipeline"
      >
        {[
          "Source",
          "Artifact extraction",
          "Normalization",
          "Entity resolution",
          "Cross-source correlation",
          "Confidence",
          "Analyst review",
        ].map((s, i, all) => (
          <span key={s}>
            <small>{String(i + 1).padStart(2, "0")}</small>
            {s}
            {i < all.length - 1 && <span className="wb-pipeline-arrow">→</span>}
          </span>
        ))}
      </div>
      <nav className="wb-tabs" aria-label="Persona toolkit navigation">
        {[
          ["/overview", "Overview"],
          ["/graph", "Correlation graph"],
          ["/dossier", "Persona dossiers"],
          ["/timeline", "Activity timeline"],
        ].map(([to, label]) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => (isActive ? "selected" : "")}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="wb-toolkit-content">{children}</div>
    </div>
  );
}

function Shell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [guide, setGuide] = useState(false);
  const [menu, setMenu] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    function shortcut(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        input.current?.focus();
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  const toolkitActive = ["/overview", "/graph", "/dossier", "/timeline"].some(
    (path) => location.pathname.startsWith(path),
  );
  const nav = [
    { label: "Command center", to: "/command", icon: LayoutDashboard },
    { label: "Threat intelligence", to: "/intelligence", icon: Search },
    { label: "Investigations", to: "/investigations", icon: FolderOpen },
    { label: "Threat actors", to: "/actors", icon: Users },
    { label: "Assets", to: "/assets", icon: Server },
    { label: "Dark-web intelligence", to: "/dark-web", icon: Radar },
    { label: "NIST alignment", to: "/nist", icon: ShieldCheck },
    { label: "Reports", to: "/reports", icon: FileText },
  ];
  return (
    <div className="wb-app">
      <a className="wb-skip-link" href="#main-content">
        Skip to main content
      </a>
      <aside className={`wb-sidebar ${menu ? "open" : ""}`}>
        <Link
          className="wb-brand"
          to="/command"
          aria-label="Gothamite command center"
        >
          <svg viewBox="0 0 28 28" width="29" height="29" aria-hidden="true">
            <path
              d="M4 8 14 2l10 6v12l-10 6-10-6V8Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            />
            <path
              d="M19 10h-7l-4 4 4 5h7v-5h-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
            />
          </svg>
          <span>
            GOTHAMITE<small>INTELLIGENCE WORKSPACE</small>
          </span>
        </Link>
        <div className="wb-workspace-label">
          <span className="wb-workspace-mark">M</span>
          <span>
            Meridian Research<small>Exercise workspace</small>
          </span>
        </div>
        <div className="wb-nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation" onClick={() => setMenu(false)}>
          {nav.map((item, i) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `${isActive ? "active" : ""} ${i === 6 ? "wb-nav-separator" : ""}`
              }
            >
              <item.icon size={16} strokeWidth={1.6} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="wb-sidebar-bottom">
          <div className="wb-nav-label">EXISTING TOOLKIT</div>
          <NavLink
            className={`wb-legacy-link ${toolkitActive ? "active" : ""}`}
            to="/overview"
            onClick={() => setMenu(false)}
          >
            <Network size={15} />
            Persona correlation
            <ArrowUpRight size={12} />
          </NavLink>
          <button className="wb-demo-guide" onClick={() => setGuide(true)}>
            <span>
              <i />
              DEMO ENVIRONMENT
            </span>
            <small>Learn the investigation path ↗</small>
          </button>
          <p>
            All intelligence is synthetic.
            <br />
            All response actions are simulated.
          </p>
        </div>
      </aside>
      <div className="wb-main-shell">
        <header className="wb-topbar">
          <button
            className="wb-icon-button wb-menu-button"
            aria-label="Toggle navigation"
            onClick={() => setMenu((v) => !v)}
          >
            <Menu size={20} />
          </button>
          <form
            className="wb-global-search"
            onSubmit={(e) => {
              e.preventDefault();
              navigate(`/intelligence?q=${encodeURIComponent(query.trim())}`);
            }}
          >
            <Search size={17} />
            <input
              ref={input}
              aria-label="Global search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search IOC, entity or incident · e.g. 203.0.113.42"
              maxLength={256}
            />
            <kbd>Ctrl K</kbd>
          </form>
          <div className="wb-topbar-right">
            <span className="wb-environment">
              <i />
              SYNTHETIC EXERCISE
            </span>
            <span className="wb-topbar-divider" />
            <div className="wb-analyst">
              <span className="wb-avatar">DA</span>
              <span>
                Demo analyst<small>Local analyst seat</small>
              </span>
            </div>
          </div>
        </header>
        <main id="main-content" className="wb-main" tabIndex={-1}>
          <WorkbenchBoundary>
            <Suspense
              fallback={
                <ResourceState loading retry={() => window.location.reload()} />
              }
            >
              <Routes>
                <Route path="/" element={<Navigate to="/command" replace />} />
                <Route path="/command" element={<CommandCenter />} />
                <Route
                  path="/intelligence"
                  element={<Intelligence key={location.search} />}
                />
                <Route
                  path="/intelligence/:id"
                  element={<EntityProfile key={location.pathname} />}
                />
                <Route
                  path="/investigations"
                  element={<CommandCenter listOnly />}
                />
                <Route
                  path="/incidents"
                  element={<Navigate to="/investigations" replace />}
                />
                <Route
                  path="/investigations/:id"
                  element={<Investigation key={location.pathname} />}
                />
                <Route
                  path="/actors"
                  element={<Intelligence key="actors" catalog="actors" />}
                />
                <Route
                  path="/assets"
                  element={<Intelligence key="assets" catalog="assets" />}
                />
                <Route
                  path="/dark-web"
                  element={<Intelligence key="darkweb" catalog="darkweb" />}
                />
                <Route path="/nist" element={<NistOverview />} />
                <Route path="/reports" element={<Reports />} />
                <Route
                  path="/overview"
                  element={
                    <ToolkitFrame>
                      <LegacyOverview />
                    </ToolkitFrame>
                  }
                />
                <Route
                  path="/graph"
                  element={
                    <ToolkitFrame>
                      <LegacyGraph />
                    </ToolkitFrame>
                  }
                />
                <Route
                  path="/dossier"
                  element={
                    <ToolkitFrame>
                      <LegacyDossier />
                    </ToolkitFrame>
                  }
                />
                <Route
                  path="/dossier/:personaId"
                  element={
                    <ToolkitFrame>
                      <LegacyDossier />
                    </ToolkitFrame>
                  }
                />
                <Route
                  path="/timeline"
                  element={
                    <ToolkitFrame>
                      <LegacyTimeline />
                    </ToolkitFrame>
                  }
                />
                <Route
                  path="*"
                  element={
                    <div className="wb-empty">
                      <h1>View not found</h1>
                      <Link className="wb-button" to="/command">
                        Return to command center
                      </Link>
                    </div>
                  }
                />
              </Routes>
            </Suspense>
          </WorkbenchBoundary>
        </main>
        <footer className="wb-footer">
          <span>
            GOTHAMITE <i>/</i> Evidence before inference.
          </span>
          <span>
            Exercise snapshot · 28 Sep 2026 <i>/</i> CSF 2.0 workflow
          </span>
        </footer>
      </div>
      {guide && <DemoGuide onClose={() => setGuide(false)} />}
    </div>
  );
}

export default function WorkbenchApp() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}
