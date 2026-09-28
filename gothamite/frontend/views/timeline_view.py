from html import escape as escape_html
import streamlit as st
from frontend.api_client import get_timeline_all_events


def render_timeline(graph_data):
    st.html('<h2>04 &mdash; ANALYZE / TIMELINE</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Identifier observations in chronological order, "
            "each traced to the source artifact it was extracted from. Synthetic corpus.</div>")
    st.markdown("---")

    st.html('<h4>IDENTIFIER OBSERVATION TIMELINE</h4>')
    events = get_timeline_all_events()
    if not events:
        st.info("No observations recorded.")
        return

    for ev in events:
        st.html(
            "<div style='padding: 12px 15px; border-left: 2px solid #38bdf8; margin: 0 0 14px 10px; background-color: #0f172a;'>"
            f"<div style='color: #64748b; font-size: 0.75rem; font-family: monospace;'>{escape_html(str(ev.get('observed_at') or 'undated'))} UTC</div>"
            f"<div style='color: #f8fafc; font-weight: 600;'>{escape_html(str(ev.get('handle')))} · {escape_html(str(ev.get('identifier_type')))}</div>"
            f"<div style='color: #cbd5e1; font-size: 0.85rem; font-family: monospace; word-break: break-all;'>{escape_html(str(ev.get('identifier_value')))}</div>"
            f"<div style='color: #64748b; font-size: 0.75rem;'>Source {escape_html(str(ev.get('source_id')))} · artifact {escape_html(str(ev.get('artifact_id')))}</div>"
            "</div>"
        )
