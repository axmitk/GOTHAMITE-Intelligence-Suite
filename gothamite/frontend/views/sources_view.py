from html import escape as escape_html
import streamlit as st
import pandas as pd

def render_sources(sources_data):
    st.html("<h2 style='color: #e2e8f0;'>SOURCE INTELLIGENCE</h2>")
    st.markdown("---")
    
    if not sources_data:
        st.html("<div style='color: #64748b;'>NO SOURCE DATA.</div>")
        return
        
    cols = st.columns(min(len(sources_data), 3))
    for idx, s in enumerate(sources_data):
        with cols[idx % len(cols)]:
            st.html(f"<div style='border: 1px solid #334155; padding: 20px; border-radius: 4px; background-color: #0f172a; margin-bottom: 20px;'><div style='font-size: 1.2rem; color: #f8fafc; font-weight: 600; margin-bottom: 15px;'>{escape_html(f'{s['source_id']}')}</div><table style='width: 100%; border-collapse: collapse;'><tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Type</td><td style='color: #e2e8f0; text-align: right;'>{escape_html(f'{s['type'].capitalize()}')}</td></tr><tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Artifacts</td><td style='color: #e2e8f0; text-align: right;'>{escape_html(f'{s['artifacts_count']}')}</td></tr><tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Entities</td><td style='color: #e2e8f0; text-align: right;'>{escape_html(f'{s['personas_count']}')}</td></tr><tr><td style='padding: 5px 0; color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;'>Status</td><td style='color: #10b981; text-align: right;'>{escape_html(f'{s['status'].upper()}')}</td></tr></table></div>")
            
    st.html("<br><h4 style='color: #cbd5e1;'>SOURCE LIST</h4>")
    df = pd.DataFrame(sources_data)
    st.dataframe(df[["source_id", "type", "personas_count", "artifacts_count", "status", "last_scan"]], width='stretch', hide_index=True)
