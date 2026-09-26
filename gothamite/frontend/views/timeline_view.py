import streamlit as st
import pandas as pd

def render_timeline(graph_data):
    st.markdown("<h2>04 &mdash; ANALYZE / TIMELINE</h2>", unsafe_allow_html=True)
    st.markdown("<div style='color: #94a3b8; margin-bottom: 20px;'>Chronological intelligence events combining multiple sources.</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("<h4>INVESTIGATION TIMELINE</h4>", unsafe_allow_html=True)
    
    nodes = graph_data.get("nodes", [])
    if not nodes:
        st.info("No timeline events available.")
        return
        
    st.markdown("""
    <style>
    .timeline-item {
        padding: 15px;
        border-left: 2px solid #38bdf8;
        margin-bottom: 20px;
        background-color: #0f172a;
        margin-left: 10px;
        position: relative;
    }
    .timeline-item::before {
        content: '';
        position: absolute;
        width: 10px;
        height: 10px;
        background-color: #38bdf8;
        border-radius: 50%;
        left: -6px;
        top: 20px;
    }
    .timeline-date { color: #94a3b8; font-size: 0.8rem; font-family: monospace; }
    .timeline-title { color: #f8fafc; font-weight: 600; font-size: 1.05rem; margin: 4px 0; }
    .timeline-source { color: #10b981; font-size: 0.8rem; font-weight: 600; }
    .timeline-desc { color: #cbd5e1; font-size: 0.9rem; margin-top: 8px; }
    </style>
    """, unsafe_allow_html=True)
    
    events = [
        {"date": "2026-09-21 14:22:05 UTC", "title": "New Alias Discovered: nightjar", "source": "forum-alpha (Dark Web)", "desc": "Entity extracted from observed forum artifact. Profile creation detected."},
        {"date": "2026-09-22 09:15:33 UTC", "title": "Infrastructure Correlated: PGP Key Match", "source": "CORRELATION ENGINE", "desc": "nightjar linked to previously known identity ven0m via exact PGP fingerprint match (Confidence: 0.95)."},
        {"date": "2026-09-23 18:40:12 UTC", "title": "Marketplace Activity: Cryptocurrency Wallet Exposed", "source": "marketplace-beta", "desc": "Wallet address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa extracted from listing associated with ven0m."},
        {"date": "2026-09-24 22:05:41 UTC", "title": "Domain Resolution", "source": "Browser Intelligence Layer", "desc": "Infrastructure mapped: Wallet previously linked to vendor on shadow_market.onion."},
        {"date": "2026-09-25 04:12:00 UTC", "title": "Risk Escalation", "source": "RISK ENGINE", "desc": "Entity risk score elevated to CRITICAL due to confirmed marketplace interactions and shared infrastructure."}
    ]
    
    for ev in events:
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-date">{ev['date']}</div>
            <div class="timeline-title">{ev['title']}</div>
            <div class="timeline-source">SOURCE: {ev['source']}</div>
            <div class="timeline-desc">{ev['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
