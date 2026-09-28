import json
import pandas as pd
import streamlit as st
from frontend.api_client import get_all_personas, get_graph, get_sources_metrics

def render_export():
    st.html("<h3 style='color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; margin-top: 20px;'>DATA EXPORT</h3>")
    
    personas = get_all_personas()
    graph_data = get_graph()
    
    # CSV Export
    df = pd.DataFrame(personas)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download CSV Report",
        data=csv,
        file_name='gothamite_intelligence.csv',
        mime='text/csv',
        width='stretch'
    )
    
    # JSON Export
    json_str = json.dumps(graph_data, indent=2)
    st.download_button(
        label="Download JSON Graph",
        data=json_str,
        file_name='gothamite_graph.json',
        mime='application/json',
        width='stretch'
    )

