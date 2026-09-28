from html import escape as escape_html
import streamlit as st
import pandas as pd
from frontend.api_client import get_all_personas, get_persona_dossier, get_artifact

def render_entities(graph_data):
    st.html("<h2 style='color: #e2e8f0;'>ENTITIES & DOSSIERS</h2>")
    st.markdown("---")
    
    personas = get_all_personas()
    if not personas:
        st.html("<div style='color: #64748b;'>NO INVESTIGATION DATA.</div>")
        return
        
    edges = graph_data.get("edges", [])
    
    col_list, col_dossier = st.columns([1, 1])
    
    with col_list:
        st.html("<h4 style='color: #cbd5e1;'>ENTITY LIST</h4>")
        rows = []
        for p in personas:
            pid = p['persona_id']
            # Find correlations for this persona
            p_edges = [e for e in edges if e['from_node'] == pid or e['to_node'] == pid]
            # Check for rejections
            rejected = [e for e in p_edges if e.get('status') == 'rejected']
            active = [e for e in p_edges if e.get('status') != 'rejected']
            
            if active:
                status = "Correlated"
            elif rejected:
                status = "Rejected"
            else:
                status = "Isolated"
                
            rows.append({
                "ENTITY": p['handle'],
                "TYPE": "Persona",
                "SOURCE": p['source_id'],
                "CORRELATIONS": len(p_edges),
                "STATUS": status,
                "_id": pid
            })
            
        df = pd.DataFrame(rows)
        # Using AgGrid or just st.dataframe with selection
        # For simplicity and native support without extra deps, we use st.dataframe
        # but to select, we use a selectbox or radio button above the dossier
        st.dataframe(df.drop(columns=["_id"]), width='stretch', hide_index=True)
        
    with col_dossier:
        st.html("<h4 style='color: #cbd5e1;'>ENTITY DOSSIER</h4>")
        
        options = {f"{r['ENTITY']} ({r['SOURCE']})": r['_id'] for r in rows}
        selected_label = st.selectbox("Select entity to view dossier", list(options.keys()), label_visibility="collapsed")
        
        dossier = get_persona_dossier(options[selected_label])
        if dossier:
            st.html(f"<div style='border: 1px solid #334155; padding: 20px; border-radius: 4px; background-color: #0f172a;'><div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;'>Entity</div><div style='font-size: 1.5rem; color: #f8fafc; font-weight: 600; margin-bottom: 20px;'>{escape_html(f'{dossier['handle'].upper()}')}</div><div style='display: flex; justify-content: space-between; margin-bottom: 20px;'><div><div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;'>Entity Type</div><div style='color: #e2e8f0;'>Persona</div></div><div><div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase;'>Source Coverage</div><div style='color: #e2e8f0;'>{escape_html(f'{dossier['source_id']}')}</div></div></div>")
            
            st.html("<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px;'>IDENTIFIERS</div>")
            identifiers = dossier.get("identifiers", [])
            if not identifiers:
                st.html("<div style='color: #64748b;'>None extracted</div>")
            for ident in identifiers:
                st.html(f"<div style='margin-bottom: 10px;'><div style='color: #e2e8f0; font-weight: 500;'>{escape_html(f'{ident['type'].upper()}')}</div><div style='color: #3b82f6; font-family: monospace;'>{escape_html(f'{ident['value']}')}</div></div>")
                
            st.html("<div style='font-size: 0.85rem; color: #94a3b8; text-transform: uppercase; margin-top: 20px; margin-bottom: 10px;'>CORRELATION</div>")
            links = dossier.get("correlated_links", [])
            if not links:
                st.html("<div style='color: #64748b;'>0 correlations</div>")
            for lk in links:
                color = "#ef4444" if lk.get("status") == "rejected" else "#10b981"
                st.html(f"<div style='border-left: 2px solid {escape_html(f'{color}')}; padding-left: 10px; margin-bottom: 10px;'><div style='color: #e2e8f0;'>Connected: <span style='font-weight: 600;'>{escape_html(f'{lk.get('target_handle')}')}</span></div><div style='color: #94a3b8;'>Score: {escape_html(f'{lk.get('score')}')} | Status: {escape_html(f'{lk.get('status').upper()}')}</div></div>")
                
            st.html('</div>')
