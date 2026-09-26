import streamlit as st
import pandas as pd
from datetime import datetime

def render_discover(graph_data):
    st.markdown("<h2>01 &mdash; DISCOVER / IDENTIFY</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; margin-bottom: 20px;'>Asset and entity discovery aligned to NIST Identify function.</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.text_input("Entity Search (Handle, Email, Domain, Wallet, Hash)", placeholder="e.g. nightjar, 0x123...")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<h4>RECENT ENTITY EXTRACTS</h4>", unsafe_allow_html=True)
        nodes = graph_data.get("nodes", [])
        if not nodes:
            st.info("No entities discovered yet.")
        else:
            for n in nodes[:5]:
                st.markdown(f"<div style='background-color: #0f172a; border-left: 3px solid #38bdf8; padding: 10px; margin-bottom: 8px;'><span style='color: #f8fafc; font-weight: 600;'>{n.get('handle')}</span><br><span style='color: #64748b; font-size: 0.8rem; font-family: monospace;'>ID: {n['id']}</span></div>", unsafe_allow_html=True)
                
    with col2:
        st.markdown("<h4>THREAT SURFACE MAPPING</h4>", unsafe_allow_html=True)
        st.markdown("<div style='background-color: #0f172a; padding: 15px; border: 1px solid #1e293b;'><ul style='color: #cbd5e1; font-size: 0.9rem;'><li>12 Dark Web Domains</li><li>4 Active Forums</li><li>3 PGP Keys Identified</li><li>8 Cryptocurrency Wallets</li></ul></div>", unsafe_allow_html=True)
        
    with col3:
        st.markdown("<h4>IDENTITY RESOLUTION QUEUE</h4>", unsafe_allow_html=True)
        st.markdown("<div style='background-color: #0f172a; padding: 10px; margin-bottom: 8px; border: 1px solid #1e293b;'><div style='color: #f8fafc; font-weight: 600; font-size: 0.9rem;'>nightjar <span style='color: #64748b;'>may be</span> ven0m</div><div style='color: #10b981; font-size: 0.8rem;'>Shared PGP Key (Confidence: HIGH)</div></div>", unsafe_allow_html=True)
        st.markdown("<div style='background-color: #0f172a; padding: 10px; margin-bottom: 8px; border: 1px solid #1e293b;'><div style='color: #f8fafc; font-weight: 600; font-size: 0.9rem;'>shadow_broker <span style='color: #64748b;'>may be</span> anon_23</div><div style='color: #f59e0b; font-size: 0.8rem;'>Temporal Proximity (Confidence: MED)</div></div>", unsafe_allow_html=True)


def render_collect(sources_data):
    st.markdown("<h2>02 &mdash; COLLECT / DETECT</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; margin-bottom: 20px;'>Continuous intelligence collection and anomaly detection mapped to NIST Detect function.</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("<h4>LLM-POWERED INTELLIGENCE PIPELINE (OLLAMA INTEGRATION)</h4>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display: flex; justify-content: space-between; align-items: center; background-color: #0f172a; padding: 20px; border: 1px solid #1e293b; margin-bottom: 20px;'>
        <div style='text-align: center; color: #38bdf8;'><div style='font-weight: 600;'>SOURCE</div><div style='font-size: 0.8rem; color: #64748b;'>Web Scraper</div></div>
        <div style='color: #475569;'>→</div>
        <div style='text-align: center; color: #38bdf8;'><div style='font-weight: 600;'>EXTRACT</div><div style='font-size: 0.8rem; color: #64748b;'>Parsing DB</div></div>
        <div style='color: #475569;'>→</div>
        <div style='text-align: center; color: #8b5cf6;'><div style='font-weight: 600;'>OLLAMA LLM</div><div style='font-size: 0.8rem; color: #64748b;'>Stylometric Analysis</div></div>
        <div style='color: #475569;'>→</div>
        <div style='text-align: center; color: #10b981;'><div style='font-weight: 600;'>NORMALIZE</div><div style='font-size: 0.8rem; color: #64748b;'>Resolution</div></div>
        <div style='color: #475569;'>→</div>
        <div style='text-align: center; color: #10b981;'><div style='font-weight: 600;'>CORRELATE</div><div style='font-size: 0.8rem; color: #64748b;'>Graph Engine</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4>INTELLIGENCE SOURCES</h4>", unsafe_allow_html=True)
        if not sources_data:
            st.info("No sources connected.")
        else:
            for s in sources_data:
                st.markdown(f"<div style='background-color: #0f172a; padding: 12px; margin-bottom: 8px; border-left: 3px solid #6366f1;'><div style='color: #f8fafc; font-weight: 600;'>{s['source_id']}</div><div style='color: #64748b; font-size: 0.85rem;'>{s.get('artifacts_count', 0)} Artifacts Extracted</div></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h4>DETECTION ALERTS</h4>", unsafe_allow_html=True)
        st.markdown("<div style='background-color: #1e1b4b; border-left: 3px solid #8b5cf6; padding: 12px; margin-bottom: 8px;'><div style='color: #c4b5fd; font-size: 0.75rem; font-weight: 600;'>NEW CORRELATION (Ollama)</div><div style='color: #f8fafc; font-size: 0.9rem;'>Previously unrelated identities connected via linguistic stylometry.</div></div>", unsafe_allow_html=True)
        st.markdown("<div style='background-color: #281021; border-left: 3px solid #be185d; padding: 12px; margin-bottom: 8px;'><div style='color: #fbcfe8; font-size: 0.75rem; font-weight: 600;'>INFRASTRUCTURE CHANGE</div><div style='color: #f8fafc; font-size: 0.9rem;'>Entity 'nightjar' associated with new .onion domain.</div></div>", unsafe_allow_html=True)


def render_risk(graph_data):
    st.markdown("<h2>05 &mdash; ASSESS / RISK ENGINE</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; margin-bottom: 20px;'>Analytical risk model determining priority and exposure. Risk = Exposure + Threat Indicators + Correlation Strength.</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("<h4>HIGH-PRIORITY ENTITIES</h4>", unsafe_allow_html=True)
        
        nodes = graph_data.get("nodes", [])
        if nodes:
            # Simulate Risk scoring
            risk_data = []
            for i, n in enumerate(nodes[:5]):
                base_risk = 95 - (i * 12)
                level = "CRITICAL" if base_risk > 80 else "HIGH" if base_risk > 60 else "MEDIUM"
                risk_data.append({
                    "Entity": n.get("handle"),
                    "Risk Score": f"{base_risk}/100",
                    "Level": level,
                    "Key Driver": "Shared Infrastructure" if i % 2 == 0 else "LLM Threat Inference",
                    "Confidence": "HIGH" if i < 3 else "MED"
                })
            
            st.dataframe(pd.DataFrame(risk_data), use_container_width=True)
            
    with col2:
        st.markdown("<h4>RISK DISTRIBUTION</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style='padding: 20px; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 4px;'>
            <div style='margin-bottom: 15px;'>
                <div style='display: flex; justify-content: space-between; color: #f8fafc; font-size: 0.85rem; margin-bottom: 4px;'><span>CRITICAL</span><span>12%</span></div>
                <div style='width: 100%; background-color: #1e293b; height: 8px; border-radius: 4px;'><div style='width: 12%; background-color: #ef4444; height: 100%; border-radius: 4px;'></div></div>
            </div>
            <div style='margin-bottom: 15px;'>
                <div style='display: flex; justify-content: space-between; color: #f8fafc; font-size: 0.85rem; margin-bottom: 4px;'><span>HIGH</span><span>28%</span></div>
                <div style='width: 100%; background-color: #1e293b; height: 8px; border-radius: 4px;'><div style='width: 28%; background-color: #f59e0b; height: 100%; border-radius: 4px;'></div></div>
            </div>
            <div style='margin-bottom: 15px;'>
                <div style='display: flex; justify-content: space-between; color: #f8fafc; font-size: 0.85rem; margin-bottom: 4px;'><span>MEDIUM</span><span>45%</span></div>
                <div style='width: 100%; background-color: #1e293b; height: 8px; border-radius: 4px;'><div style='width: 45%; background-color: #38bdf8; height: 100%; border-radius: 4px;'></div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
