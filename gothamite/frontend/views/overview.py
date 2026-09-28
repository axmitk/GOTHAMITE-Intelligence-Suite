from html import escape as escape_html
import streamlit as st
import pandas as pd

CARD = "background-color: #0f172a; padding: 15px; border: 1px solid #1e293b; border-radius: 4px;"


def _metric(label, value, note):
    st.html(
        f"<div style='{CARD}'>"
        f"<div style='color: #64748b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>{escape_html(label)}</div>"
        f"<div style='color: #f8fafc; font-size: 2rem; font-weight: 600; font-family: monospace;'>{escape_html(str(value))}</div>"
        f"<div style='color: #64748b; font-size: 0.75rem;'>{escape_html(note)}</div></div>"
    )


def render_overview(graph_data, sources_data):
    st.html('<h2>00 &mdash; WORKSTATION DASHBOARD</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Cross-source persona correlation over a synthetic source corpus. "
            "Every count below is computed from the loaded dataset; correlation uses documented, deterministic evidence weights.</div>")
    st.markdown("---")

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    proposed = [e for e in edges if e.get("status") == "proposed"]
    artifacts = sum(s.get("artifacts_count", 0) for s in sources_data)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric("Observed personas", len(nodes), "Distinct handles per source")
    with col2:
        _metric("Collected artifacts", artifacts, "Synthetic posts and listings")
    with col3:
        _metric("Candidate linkages", len(edges), "Cross-source relationships with evidence")
    with col4:
        _metric("Awaiting analyst review", len(proposed), "Proposed; not yet confirmed or rejected")

    st.html('<br>')
    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.html('<h4>COLLECTION AND CORRELATION PIPELINE</h4>')
        stages = [
            ("SOURCE", "Synthetic fixtures"), ("EXTRACT", "Handles, PGP, wallets"), ("NORMALIZE", "Canonical identifiers"),
            ("RESOLVE", "Persona per source"), ("CORRELATE", "Weighted evidence"), ("REVIEW", "Analyst decision"),
        ]
        cells = "<div style='color: #334155;'>→</div>".join(
            f"<div style='text-align: center;'><div style='font-weight: 600; font-size: 0.85rem; color: #cbd5e1;'>{escape_html(a)}</div>"
            f"<div style='font-size: 0.7rem; color: #64748b;'>{escape_html(b)}</div></div>" for a, b in stages)
        st.html(f"<div style='display: flex; justify-content: space-between; align-items: center; {CARD} margin-bottom: 8px;'>{cells}</div>")
        st.html("<div style='color: #64748b; font-size: 0.75rem; margin-bottom: 20px;'>Prototype: synthetic source fixtures. "
                "Target deployment: scheduled ingestion through source adapters into the same normalization and correlation stages.</div>")

        st.html('<h4>CANDIDATE LINKAGES BY SCORE</h4>')
        if edges:
            rows = sorted(edges, key=lambda e: e.get("score", 0), reverse=True)
            st.dataframe(pd.DataFrame([{
                "From": e.get("from_handle"), "To": e.get("to_handle"), "Score": f"{e.get('score', 0):.2f}",
                "Evidence rows": e.get("evidence_count", 0), "Review status": e.get("status"),
            } for e in rows]), width='stretch', hide_index=True)
        else:
            st.info("No candidate linkages. Run a correlation pass after loading source fixtures.")

    with col_b:
        st.html('<h4>SOURCE COLLECTION STATUS</h4>')
        if not sources_data:
            st.info("No sources loaded.")
        for s in sources_data:
            st.html(
                f"<div style='{CARD} margin-bottom: 8px;'>"
                f"<div style='display: flex; justify-content: space-between;'><span style='color: #f8fafc; font-weight: 600; font-family: monospace;'>{escape_html(str(s.get('source_id')))}</span>"
                f"<span style='color: #94a3b8; font-size: 0.75rem;'>SYNTHETIC SOURCE</span></div>"
                f"<div style='color: #94a3b8; font-size: 0.8rem;'>{escape_html(str(s.get('type')))} · reliability {escape_html(str(s.get('reliability')))} · "
                f"{escape_html(str(s.get('artifacts_count', 0)))} artifacts · last ingestion {escape_html(str(s.get('last_scan', 'never'))[:10])}</div></div>"
            )
        st.html("<div style='color: #64748b; font-size: 0.75rem;'>No live connector is attached. Sources are exercise fixtures; "
                "no dark-web network is contacted.</div>")
