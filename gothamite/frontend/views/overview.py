import streamlit as st
import pandas as pd

def render_overview(graph_data, sources_data):
    st.markdown("<h2>00 &mdash; WORKSTATION DASHBOARD</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; margin-bottom: 20px;'>GOTHAMITE Operational Intelligence & Analysis Center.</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div style='background-color: #0f172a; padding: 15px; border-left: 3px solid #38bdf8; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b; border-radius: 4px;'>
            <div style='color: #64748b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>Active Investigations</div>
            <div style='color: #f8fafc; font-size: 2rem; font-weight: 600; font-family: monospace;'>12</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style='background-color: #0f172a; padding: 15px; border-left: 3px solid #ef4444; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b; border-radius: 4px;'>
            <div style='color: #64748b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>Critical Entities</div>
            <div style='color: #f8fafc; font-size: 2rem; font-weight: 600; font-family: monospace;'>3</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style='background-color: #0f172a; padding: 15px; border-left: 3px solid #10b981; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b; border-radius: 4px;'>
            <div style='color: #64748b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>New Correlations</div>
            <div style='color: #f8fafc; font-size: 2rem; font-weight: 600; font-family: monospace;'>8</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div style='background-color: #0f172a; padding: 15px; border-left: 3px solid #8b5cf6; border-top: 1px solid #1e293b; border-right: 1px solid #1e293b; border-bottom: 1px solid #1e293b; border-radius: 4px;'>
            <div style='color: #64748b; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;'>Detection Signals</div>
            <div style='color: #f8fafc; font-size: 2rem; font-weight: 600; font-family: monospace;'>45</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown("<h4>NIST CSF OPERATIONAL WORKFLOW</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style='display: flex; justify-content: space-between; align-items: center; background-color: #0f172a; padding: 20px; border: 1px solid #1e293b; margin-bottom: 20px;'>
            <div style='text-align: center; color: #38bdf8;'><div style='font-weight: 600; font-size: 0.9rem;'>IDENTIFY</div><div style='font-size: 0.7rem; color: #64748b;'>Asset Discovery</div></div>
            <div style='color: #334155;'>→</div>
            <div style='text-align: center; color: #10b981;'><div style='font-weight: 600; font-size: 0.9rem;'>PROTECT</div><div style='font-size: 0.7rem; color: #64748b;'>Risk Priority</div></div>
            <div style='color: #334155;'>→</div>
            <div style='text-align: center; color: #f59e0b;'><div style='font-weight: 600; font-size: 0.9rem;'>DETECT</div><div style='font-size: 0.7rem; color: #64748b;'>Continuous Intel</div></div>
            <div style='color: #334155;'>→</div>
            <div style='text-align: center; color: #ef4444;'><div style='font-weight: 600; font-size: 0.9rem;'>RESPOND</div><div style='font-size: 0.7rem; color: #64748b;'>Correlation / Analysis</div></div>
            <div style='color: #334155;'>→</div>
            <div style='text-align: center; color: #8b5cf6;'><div style='font-weight: 600; font-size: 0.9rem;'>RECOVER</div><div style='font-size: 0.7rem; color: #64748b;'>Dossier / Reporting</div></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h4>RECENT INTELLIGENCE PIPELINE ACTIVITY</h4>", unsafe_allow_html=True)
        df = pd.DataFrame([
            {"Time": "10:12:44", "Stage": "EXTRACTION", "Source": "forum-alpha", "Event": "Extracted 2 PGP Keys"},
            {"Time": "10:11:02", "Stage": "CORRELATION", "Source": "ENGINE", "Event": "Matched identity 'nightjar' -> 'ven0m'"},
            {"Time": "10:05:15", "Stage": "COLLECTION", "Source": "Browser", "Event": "Captured marketplace listing (shadow_market)"},
            {"Time": "09:58:30", "Stage": "RISK", "Source": "ENGINE", "Event": "Elevated entity risk to CRITICAL"}
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with col_b:
        st.markdown("<h4>PRIORITY ENTITIES</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background-color: #0f172a; border: 1px solid #1e293b; padding: 15px; margin-bottom: 10px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                <div style='color: #f8fafc; font-weight: 600;'>nightjar</div>
                <div style='color: #ef4444; font-size: 0.75rem; font-weight: 700; background-color: rgba(239, 68, 68, 0.1); padding: 2px 6px; border-radius: 4px;'>CRITICAL</div>
            </div>
            <div style='color: #94a3b8; font-size: 0.8rem;'>Shared PGP / Wallet Extracted</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style='background-color: #0f172a; border: 1px solid #1e293b; padding: 15px; margin-bottom: 10px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
                <div style='color: #f8fafc; font-weight: 600;'>shadow_broker</div>
                <div style='color: #f59e0b; font-size: 0.75rem; font-weight: 700; background-color: rgba(245, 158, 11, 0.1); padding: 2px 6px; border-radius: 4px;'>HIGH</div>
            </div>
            <div style='color: #94a3b8; font-size: 0.8rem;'>Marketplace Vendor Profile</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<h4>COLLECTION STATUS</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background-color: #0f172a; border: 1px solid #1e293b; padding: 15px;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #cbd5e1; font-size: 0.85rem;'>Dark Web Scrapers</span><span style='color: #10b981; font-size: 0.85rem; font-weight: 600;'>ONLINE</span></div>
            <div style='display: flex; justify-content: space-between; margin-bottom: 8px;'><span style='color: #cbd5e1; font-size: 0.85rem;'>Browser Intel Extension</span><span style='color: #10b981; font-size: 0.85rem; font-weight: 600;'>ACTIVE</span></div>
            <div style='display: flex; justify-content: space-between;'><span style='color: #cbd5e1; font-size: 0.85rem;'>Correlation Engine</span><span style='color: #10b981; font-size: 0.85rem; font-weight: 600;'>PROCESSING</span></div>
        </div>
        """, unsafe_allow_html=True)
