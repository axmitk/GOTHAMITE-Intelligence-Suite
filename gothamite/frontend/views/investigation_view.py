from html import escape as escape_html
import streamlit as st
import pandas as pd
from frontend.api_client import search_entities

CARD = "background-color: #0f172a; padding: 12px; border: 1px solid #1e293b; margin-bottom: 8px;"


def render_discover(graph_data):
    st.html('<h2>01 &mdash; DISCOVER / IDENTIFY</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Observed personas and extracted identifiers "
            "(NIST CSF Identify: ID.AM, scoped to the synthetic source corpus).</div>")
    st.markdown("---")

    query = st.text_input("Identifier search (handle, PGP fingerprint, wallet)", placeholder="e.g. nightjar")
    if query.strip():
        found = search_entities(query.strip())
        results = found.get("results", [])
        if results:
            st.dataframe(pd.DataFrame(results), width='stretch', hide_index=True)
        else:
            st.info("No matching identifier in the loaded dataset.")

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    col1, col2 = st.columns(2)
    with col1:
        st.html('<h4>OBSERVED PERSONAS</h4>')
        if not nodes:
            st.info("No personas extracted yet.")
        for n in nodes:
            st.html(f"<div style='{CARD}'><span style='color: #f8fafc; font-weight: 600; font-family: monospace;'>{escape_html(str(n.get('handle')))}</span>"
                    f"<br><span style='color: #64748b; font-size: 0.8rem;'>{escape_html(str(n.get('source_id')))} · {escape_html(str(n.get('post_count', 0)))} posts</span></div>")
    with col2:
        st.html('<h4>ENTITY RESOLUTION QUEUE</h4>')
        pending = [e for e in edges if e.get("status") == "proposed"]
        if not pending:
            st.info("No candidate linkages awaiting review.")
        for e in sorted(pending, key=lambda e: e.get("score", 0), reverse=True):
            st.html(f"<div style='{CARD}'><div style='color: #f8fafc; font-weight: 600; font-size: 0.9rem;'>{escape_html(str(e.get('from_handle')))} "
                    f"<span style='color: #64748b;'>candidate link to</span> {escape_html(str(e.get('to_handle')))}</div>"
                    f"<div style='color: #94a3b8; font-size: 0.8rem;'>Score {e.get('score', 0):.2f} · {escape_html(str(e.get('evidence_count', 0)))} evidence rows · analyst review required</div></div>")


def render_collect(sources_data):
    st.html('<h2>02 &mdash; COLLECT / DETECT</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Source collection and artifact extraction "
            "(NIST CSF Detect: DE.AE). The prototype loads synthetic source fixtures; no live collection runs.</div>")
    st.markdown("---")

    st.html('<h4>COLLECTION ARCHITECTURE</h4>')
    stages = ["Source adapters", "Scheduled ingestion", "Raw artifacts", "Normalization", "Identifier extraction", "Correlation", "Analyst review"]
    st.html("<div style='background-color: #0f172a; padding: 16px; border: 1px solid #1e293b; color: #cbd5e1; font-size: 0.85rem;'>"
            + " → ".join(escape_html(s) for s in stages) + "</div>")
    st.html("<div style='color: #64748b; font-size: 0.8rem; margin: 6px 0 20px;'>"
            "<b>Implemented prototype:</b> synthetic artifacts with SHA-256 hashes, deterministic extraction and correlation. "
            "<b>Deployment architecture:</b> scheduled or continuous ingestion through source adapters feeding the same stages.</div>")

    st.html('<h4>SOURCE COLLECTION STATUS</h4>')
    if not sources_data:
        st.info("No sources loaded.")
    else:
        st.dataframe(pd.DataFrame([{
            "Source": s.get("source_id"), "Type": s.get("type"), "Reliability": s.get("reliability"),
            "Collection": "Synthetic fixture", "Artifacts": s.get("artifacts_count", 0),
            "Personas": s.get("personas_count", 0), "Last ingestion": str(s.get("last_scan", "never"))[:10],
        } for s in sources_data]), width='stretch', hide_index=True)


def render_risk(graph_data):
    st.html('<h2>05 &mdash; ASSESS / LINKAGE PRIORITY</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Personas ordered by their strongest candidate linkage. "
            "Scores are sums of documented evidence weights (capped at 0.95), not probabilities and not incident risk. "
            "Incident risk factors are assessed in the investigation workbench.</div>")
    st.markdown("---")

    nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
    edges = graph_data.get("edges", [])
    if not edges:
        st.info("No candidate linkages to prioritize.")
        return
    rows = []
    for pid, n in nodes.items():
        linked = [e for e in edges if pid in (e.get("from_node"), e.get("to_node"))]
        if not linked:
            continue
        best = max(linked, key=lambda e: e.get("score", 0))
        rows.append({
            "Persona": n.get("handle"), "Source": n.get("source_id"), "Candidate linkages": len(linked),
            "Strongest score": round(best.get("score", 0), 2),
            "Strongest link": f"{best.get('from_handle')} → {best.get('to_handle')}",
            "Review status": best.get("status"),
        })
    st.dataframe(pd.DataFrame(sorted(rows, key=lambda r: r["Strongest score"], reverse=True)),
                 width='stretch', hide_index=True)
