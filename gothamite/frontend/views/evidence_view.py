import streamlit as st
from frontend.api_client import get_timeline_all_events, get_artifact

def render_evidence():
    st.markdown("<h2 style='color: #e2e8f0;'>EVIDENCE LOCKER</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    events = get_timeline_all_events()
    if not events:
        st.markdown("<div style='color: #64748b;'>NO EVIDENCE DATA.</div>", unsafe_allow_html=True)
        return
        
    # Get unique artifacts
    seen = set()
    unique_artifacts = []
    for ev in events:
        if ev['artifact_id'] not in seen:
            seen.add(ev['artifact_id'])
            unique_artifacts.append(ev)
            
    # Sort by time descending
    unique_artifacts = sorted(unique_artifacts, key=lambda x: x.get('observed_at', ''), reverse=True)
    
    col_list, col_viewer = st.columns([1, 2])
    
    with col_list:
        st.markdown("<h4 style='color: #cbd5e1;'>CAPTURED ARTIFACTS</h4>", unsafe_allow_html=True)
        options = {
            f"{a['source_id']} ({a['artifact_id'][:8]}...)": a['artifact_id']
            for a in unique_artifacts
        }
        selected_label = st.radio("Select Evidence", list(options.keys()), label_visibility="collapsed")
        
    with col_viewer:
        st.markdown("<h4 style='color: #cbd5e1;'>PROVENANCE VIEWER</h4>", unsafe_allow_html=True)
        if selected_label:
            art = get_artifact(options[selected_label])
            if art:
                st.markdown(
                    f"<div style='border: 1px solid #334155; padding: 20px; border-radius: 4px; background-color: #0f172a;'>"
                    f"<table style='width: 100%; border-collapse: collapse; margin-bottom: 20px;'>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>Source</td><td style='color: #e2e8f0; font-family: monospace;'>{art['source_id']}</td></tr>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>URL</td><td style='color: #3b82f6; font-family: monospace;'>{art['url']}</td></tr>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>Collected At</td><td style='color: #e2e8f0; font-family: monospace;'>{art['collected_at']}</td></tr>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>Relay Path</td><td style='color: #e2e8f0; font-family: monospace;'>{' &rarr; '.join(art.get('relay_path', []))}</td></tr>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>Artifact ID</td><td style='color: #e2e8f0; font-family: monospace;'>{art['artifact_id']}</td></tr>"
                    f"<tr><td style='padding: 5px 0; color: #94a3b8; width: 120px; text-transform: uppercase; font-size: 0.85rem;'>Artifact Hash</td><td style='color: #10b981; font-family: monospace;'>{art['content_hash']}</td></tr>"
                    f"</table>"
                    
                    f"<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px;'>RAW CONTENT</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                st.code(art['raw_content'], language="html")

