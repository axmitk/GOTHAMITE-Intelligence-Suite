import streamlit as st
import pandas as pd

def render_sources(sources_data):
    st.markdown("<h2 style='color: #e2e8f0;'>SOURCE INTELLIGENCE</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    if not sources_data:
        st.markdown("<div style='color: #64748b;'>NO SOURCE DATA.</div>", unsafe_allow_html=True)
        return
        
    cols = st.columns(min(len(sources_data), 3))
    for idx, s in enumerate(sources_data):
        with cols[idx % len(cols)]:
            st.markdown(
                f"<div style='border: 1px solid #334155; padding: 20px; border-radius: 4px; background-color: #0f172a; margin-bottom: 20px;'>"
                f"<div style='font-size: 1.2rem; color: #f8fafc; font-weight: 600; margin-bottom: 15px;'>{s['source_id']}</div>"
                f"<table style='width: 100%; border-collapse: collapse;'>"
                f"<tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Type</td><td style='color: #e2e8f0; text-align: right;'>{s['type'].capitalize()}</td></tr>"
                f"<tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Artifacts</td><td style='color: #e2e8f0; text-align: right;'>{s['artifacts_count']}</td></tr>"
                f"<tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Entities</td><td style='color: #e2e8f0; text-align: right;'>{s['personas_count']}</td></tr>"
                f"<tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Status</td><td style='color: #10b981; text-align: right;'>{s['status'].upper()}</td></tr>"
                f"</table>"
                f"</div>",
                unsafe_allow_html=True
            )
            
    st.markdown("<br><h4 style='color: #cbd5e1;'>SOURCE LIST</h4>", unsafe_allow_html=True)
    df = pd.DataFrame(sources_data)
    st.dataframe(df[["source_id", "type", "personas_count", "artifacts_count", "status", "last_scan"]], width='stretch', hide_index=True)
