from html import escape as escape_html
import sys
from pathlib import Path
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

st.set_page_config(
    page_title="GOTHAMITE | Persona Correlation",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.html('\n<style>\n    /* Professional Analytical Workstation Styling */\n    @import url(\'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap\');\n    \n    .stApp {\n        background-color: #0b0f19;\n        color: #e2e8f0;\n        font-family: \'Inter\', sans-serif !important;\n    }\n    \n    [data-testid="stSidebar"] {\n        background-color: #111827;\n        border-right: 1px solid #1e293b;\n    }\n    \n    .block-container {\n        padding-top: 2rem !important;\n        padding-bottom: 2rem !important;\n    }\n    \n    h1, h2, h3, h4, h5, h6 {\n        font-family: \'Inter\', sans-serif !important;\n        color: #f8fafc;\n        font-weight: 600;\n        letter-spacing: -0.02em;\n    }\n    \n    hr {\n        border-top: 1px solid #1e293b;\n        margin: 1.5rem 0;\n    }\n    \n    [data-testid="stDataFrame"] {\n        border: 1px solid #1e293b;\n        border-radius: 4px;\n    }\n    \n    .stRadio label {\n        color: #cbd5e1;\n        font-weight: 500;\n    }\n    \n    /* Code / Mono styling */\n    code {\n        font-family: \'JetBrains Mono\', monospace !important;\n        background-color: #1e293b !important;\n        color: #38bdf8 !important;\n        padding: 0.2em 0.4em;\n        border-radius: 3px;\n    }\n    \n    .metric-value {\n        font-family: \'JetBrains Mono\', monospace !important;\n    }\n    \n    /* Buttons */\n    button[kind="secondary"] {\n        background-color: #1e293b !important;\n        border: 1px solid #334155 !important;\n        color: #f8fafc !important;\n    }\n    button[kind="secondary"]:hover {\n        background-color: #334155 !important;\n        border-color: #475569 !important;\n    }\n    \n    button[kind="primary"] {\n        background-color: #0284c7 !important;\n        color: #ffffff !important;\n        border: none !important;\n    }\n</style>\n')

from frontend.views import overview, graph_view, dossier_view, investigation_view, timeline_view
from frontend.api_client import get_graph, get_sources_metrics

def main():
    with st.sidebar:
        st.html("<h1 style='font-size: 1.5rem; margin-bottom: 0; color: #38bdf8;'>GOTHAMITE</h1>")
        st.html("<div style='color: #64748b; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 20px; letter-spacing: 0.05em;'>Persona correlation toolkit</div>")
        
        st.markdown("---")
        
        st.html("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>INVESTIGATION WORKFLOW</div>")
        
        nav = st.radio(
            "Navigation",
            options=[
                "00 — WORKSTATION DASHBOARD",
                "01 — DISCOVER / IDENTIFY",
                "02 — COLLECT / DETECT",
                "03 — CORRELATE / GRAPH",
                "04 — ANALYZE / TIMELINE",
                "05 — ASSESS / LINKAGE PRIORITY",
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
        
        st.html("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>DATASET CONTEXT</div>")
        st.html(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{escape_html(f'{total_personas}')}</span> Observed personas</div>")
        st.html(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{escape_html(f'{total_artifacts}')}</span> Collected artifacts (synthetic)</div>")
        st.html(f"<div style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 4px;'><span class='metric-value' style='color: #38bdf8;'>{escape_html(f'{total_relationships}')}</span> Candidate linkages</div>")
        
        st.markdown("---")
        st.html("<div style='color: #64748b; font-size: 0.7rem; text-transform: uppercase; font-weight: 700; margin-bottom: 10px; letter-spacing: 0.1em;'>DATA MODE</div>")
        st.html("<div style='color: #94a3b8; font-weight: 600; font-size: 0.75rem;'>Synthetic source fixtures; no live collection</div>")
        st.html("<div style='color: #94a3b8; font-weight: 600; font-size: 0.75rem;'>Deterministic evidence-weight correlation</div>")


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
    elif nav == "05 — ASSESS / LINKAGE PRIORITY":
        investigation_view.render_risk(graph_data)
    elif nav == "06 — INVESTIGATE / DOSSIER":
        dossier_view.render_dossier(graph_data)

if __name__ == "__main__":
    main()
