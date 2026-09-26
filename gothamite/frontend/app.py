import sys
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

st.set_page_config(
    page_title="GOTHAMITE | Intelligence Suite",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Professional Analytical Workstation Styling */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1e293b;
    }
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: #f8fafc;
        font-weight: 600;
        letter-spacing: -0.02em;
    }
    
    hr {
        border-top: 1px solid #1e293b;
        margin: 1.5rem 0;
    }
    
    [data-testid="stDataFrame"] {
        border: 1px solid #1e293b;
        border-radius: 4px;
    }
    
    .stRadio label {
        color: #cbd5e1;
        font-weight: 500;
    }
    
    /* Code / Mono styling */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        padding: 0.2em 0.4em;
        border-radius: 3px;
    }
    
    .metric-value {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    /* Buttons */
    button[kind="secondary"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        color: #f8fafc !important;
    }
    button[kind="secondary"]:hover {
        background-color: #334155 !important;
        border-color: #475569 !important;
    }
    
    button[kind="primary"] {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

from frontend.views import overview, graph_view, dossier_view, investigation_view, timeline_view
from frontend.api_client import get_graph, get_sources_metrics

def main():
    with st.sidebar:
        st.markdown("<h1 style='font-size: 1.5rem; margin-bottom: 0; color: #38bdf8;'>GOTHAMITE</h1>", unsafe_allow_html=True)
        st.markdown("<div style='color: #64748b; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 20px; letter-spacing: 0.05em;'>Cyber Intelligence Suite</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>INVESTIGATION WORKFLOW</div>", unsafe_allow_html=True)
        
        nav = st.radio(
            "Navigation",
            options=[
                "00 — WORKSTATION DASHBOARD",
                "01 — DISCOVER / IDENTIFY",
                "02 — COLLECT / DETECT",
                "03 — CORRELATE / GRAPH",
                "04 — ANALYZE / TIMELINE",
                "05 — ASSESS / RISK",
                "06 — INVESTIGATE / DOSSIER"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        graph_data = get_graph()
        sources_data = get_sources_metrics()
        
        total_artifacts = sum(s.get("artifacts_count", 0) for s in sources_data)
        total_personas = len(graph_data.get("nodes", []))
        total_relationships = len(graph_data.get("edges", []))
        
        st.markdown("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>DATASET CONTEXT</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{total_personas}</span> Entities Extracted</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{total_artifacts}</span> Intelligence Artifacts</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{total_relationships}</span> Asserted Correlations</div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>OPERATIONAL LAYER</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #10b981; font-weight: 600; font-size: 0.75rem;'>NIST CSF: ALIGNED</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #10b981; font-weight: 600; font-size: 0.75rem;'>CORRELATION ENGINE: ACTIVE</div>", unsafe_allow_html=True)


    if nav == "00 — WORKSTATION DASHBOARD":
        overview.render_overview(graph_data, sources_data)
    elif nav == "01 — DISCOVER / IDENTIFY":
        investigation_view.render_discover(graph_data)
    elif nav == "02 — COLLECT / DETECT":
        investigation_view.render_collect(sources_data)
    elif nav == "03 — CORRELATE / GRAPH":
        graph_view.render_graph(graph_data)
    elif nav == "04 — ANALYZE / TIMELINE":
        timeline_view.render_timeline(graph_data)
    elif nav == "05 — ASSESS / RISK":
        investigation_view.render_risk(graph_data)
    elif nav == "06 — INVESTIGATE / DOSSIER":
        dossier_view.render_dossier(graph_data)

if __name__ == "__main__":
    main()
