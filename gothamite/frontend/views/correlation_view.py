import streamlit as st
from frontend.api_client import get_edge_details, trigger_correlation

def render_correlation(graph_data):
    st.markdown("<h2 style='color: #e2e8f0;'>CORRELATION ANALYSIS</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_trigger, col_empty = st.columns([1, 3])
    with col_trigger:
        if st.button("RUN ENGINE PASS", type="primary", width='stretch'):
            with st.spinner("Executing deterministic correlation pass..."):
                res = trigger_correlation()
                st.success(f"Pass complete. Evaluated {res.get('evaluated_pairs', 0)} pairs.")
                st.rerun()
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    edges = graph_data.get("edges", [])
    if not edges:
        st.markdown("<div style='color: #64748b;'>NO CORRELATION DATA.</div>", unsafe_allow_html=True)
        return
        
    for e in edges:
        edge_details = get_edge_details(e["id"])
        if not edge_details:
            continue
            
        score = edge_details.get("score", 0.0)
        status = edge_details.get("status", "proposed")
        h1 = edge_details['from_persona']['handle']
        h2 = edge_details['to_persona']['handle']
        
        # Determine styling based on score and status
        if status == "rejected":
            border_color = "#ef4444"
            status_text = "IDENTITY LINK REJECTED"
        elif score >= 0.8:
            border_color = "#10b981"
            status_text = "IDENTITY LINK CONFIRMED" if status == "confirmed" else "STRONG IDENTITY LINK"
        elif score >= 0.3:
            border_color = "#3b82f6"
            status_text = "MODERATE IDENTITY LINK"
        else:
            border_color = "#64748b"
            status_text = "WEAK SIGNAL"
            
        st.markdown(
            f"<div style='border-top: 4px solid {border_color}; background-color: #0f172a; padding: 20px; border-radius: 4px; margin-bottom: 20px;'>"
            f"<div style='text-align: center; margin-bottom: 20px;'>"
            f"<div style='font-size: 1.5rem; color: #e2e8f0; font-weight: 600; text-transform: uppercase;'>{h1}</div>"
            f"<div style='color: #64748b; font-size: 1.2rem;'>&#8597;</div>"
            f"<div style='font-size: 1.5rem; color: #e2e8f0; font-weight: 600; text-transform: uppercase;'>{h2}</div>"
            f"</div>"
            f"<div style='text-align: center; margin-bottom: 20px;'>"
            f"<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;'>Correlation Score</div>"
            f"<div style='color: {border_color}; font-size: 2rem; font-weight: bold;'>{score:.2f}</div>"
            f"</div>"
            f"<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px;'>Signals</div>",
            unsafe_allow_html=True
        )
        
        for ev in edge_details.get("evidence", []):
            is_supp = ev.get("direction") == "supporting"
            color = "#10b981" if is_supp else "#ef4444"
            sign = "+" if is_supp else "-"
            st.markdown(
                f"<div style='display: flex; justify-content: space-between; border-bottom: 1px solid #1e293b; padding: 5px 0;'>"
                f"<div style='color: #e2e8f0;'>{ev.get('signal_type', '').replace('_', ' ').capitalize()}</div>"
                f"<div style='color: {color}; font-family: monospace;'>{sign}{abs(ev.get('weight', 0.0)):.2f}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            
        st.markdown(
            f"<div style='margin-top: 20px;'>"
            f"<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;'>Result</div>"
            f"<div style='color: {border_color}; font-weight: 600;'>{status_text}</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True
        )


