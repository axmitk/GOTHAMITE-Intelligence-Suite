from html import escape as escape_html
import streamlit as st
import streamlit.components.v1 as components
from frontend.api_client import get_edge_details, update_edge_status, get_artifact
import json

def render_graph(graph_data):
    st.html('<h2>03 &mdash; CORRELATE / ENTITY GRAPH</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Cross-source entity resolution: candidate linkages with weighted, artifact-backed evidence (NIST CSF Detect: DE.AE).</div>")
    st.markdown("---")
    
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    if not nodes:
        st.html("<div style='color: #64748b;'>NO INVESTIGATION DATA.</div>")
        return
        
    col_graph, col_inspector = st.columns([3, 2])
    
    with col_graph:
        st.html('<h4>RELATIONSHIP NETWORK</h4>')
        
        graph_nodes = []
        for n in nodes:
            graph_nodes.append({
                "id": n["id"],
                "name": n.get("handle"),
                "color": "#38bdf8",
                "val": 1.5
            })
            
        graph_links = []
        for e in edges:
            if e.get("status") == "rejected":
                continue
            score = e.get("score", 0.0)
            graph_links.append({
                "source": e["from_node"],
                "target": e["to_node"],
                "color": "#0ea5e9" if score > 0.7 else "#475569",
                "width": max(0.5, score * 2)
            })
            
        graph_data_json = json.dumps({"nodes": graph_nodes, "links": graph_links})
        
        html_code = f"""
        <html>
        <head>
          <style> body {{ margin: 0; background-color: #0b0f19; }} </style>
          <script src="https://unpkg.com/three@0.138.3/build/three.min.js"></script>
          <script src="https://unpkg.com/3d-force-graph@1.70.10"></script>
        </head>
        <body>
          <div id="3d-graph"></div>
          <script>
            const gData = {graph_data_json};
            const Graph = ForceGraph3D()
              (document.getElementById('3d-graph'))
                .backgroundColor('#0b0f19')
                .width(window.innerWidth)
                .height(600)
                .nodeLabel(node => `<div style="color: #f8fafc; background: rgba(15, 23, 42, 0.9); border: 1px solid #334155; padding: 4px; font-family: monospace; border-radius: 4px; font-size: 12px;">${{node.name}}</div>`)
                .linkWidth('width')
                .linkColor('color')
                .linkOpacity(0.4)
                .linkDirectionalParticles(d => d.width * 3)
                .linkDirectionalParticleSpeed(d => d.width * 0.005)
                .linkDirectionalParticleColor(() => '#ffffff')
                .onNodeClick(node => {{
                  const distance = 60;
                  const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                  Graph.cameraPosition(
                    {{ x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }},
                    node,
                    2000
                  );
                }})
                .nodeThreeObject(node => {{
                    const geometry = new THREE.SphereGeometry(5, 16, 16);
                    const material = new THREE.MeshBasicMaterial({{ color: '#38bdf8' }});
                    const sphere = new THREE.Mesh(geometry, material);
                    
                    const wireGeom = new THREE.SphereGeometry(6.5, 12, 12);
                    const wireMat = new THREE.MeshBasicMaterial({{ color: '#38bdf8', wireframe: true, transparent: true, opacity: 0.15 }});
                    const wireSphere = new THREE.Mesh(wireGeom, wireMat);
                    sphere.add(wireSphere);
                    return sphere;
                }})
                .graphData(gData);
                
            let angle = 0;
            setInterval(() => {{
              Graph.cameraPosition({{
                x: 150 * Math.sin(angle),
                z: 150 * Math.cos(angle)
              }});
              angle += Math.PI / 300;
            }}, 40);
          </script>
        </body>
        </html>
        """
        components.html(html_code, height=620)
        
    with col_inspector:
        st.html('<h4>CORRELATION INSPECTOR</h4>')
        
        if not edges:
            st.html("<div style='color: #64748b;'>No active relationships to inspect.</div>")
        else:
            edge_options = {
                f"{e['from_handle']} &harr; {e['to_handle']} (Conf: {e['score']})": e["id"]
                for e in edges if e["status"] != "rejected"
            }
            if not edge_options:
                st.html("<div style='color: #64748b;'>All relationships rejected.</div>")
                return
                
            selected_edge_label = st.selectbox(
                "Inspect Relationship",
                list(edge_options.keys()),
                key="graph_edge_dropdown",
            )
            selected_rel_id = edge_options[selected_edge_label]
            edge_details = get_edge_details(selected_rel_id)

            if edge_details:
                score = edge_details.get("score", 0.0)
                status_val = edge_details.get("status", "proposed")
                
                conf_color = "#10b981" if score > 0.8 else "#f59e0b" if score > 0.5 else "#ef4444"
                conf_level = "HIGH" if score > 0.8 else "MEDIUM" if score > 0.5 else "LOW"
                
                st.html(f"<div style='border: 1px solid #1e293b; padding: 15px; border-radius: 4px; background-color: #0f172a; margin-top: 10px;'><div style='font-size: 1.1rem; color: #f8fafc; font-weight: 600; text-align: center;'>{escape_html(f'{edge_details['from_persona']['handle']}')} &harr; {escape_html(f'{edge_details['to_persona']['handle']}')}</div><div style='text-align: center; color: {escape_html(f'{conf_color}')}; font-weight: bold; font-size: 1.5rem;'>{escape_html(f'{score:.2f}')} ({escape_html(f'{conf_level}')})</div><div style='text-align: center; color: #64748b; font-size: 0.8rem; text-transform: uppercase;'>Analytic Confidence</div></div>")
                
                st.html("<br><div style='font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 0.05em;'>EVIDENCE & PROVENANCE</div>")
                evidence_list = edge_details.get("evidence", [])
                for ev in evidence_list:
                    is_supporting = ev.get("direction") == "supporting"
                    sign = "+" if is_supporting else "-"
                    ev_color = "#10b981" if is_supporting else "#ef4444"
                    
                    st.html(f"<div style='border-left: 2px solid {escape_html(f'{ev_color}')}; padding-left: 10px; margin-bottom: 12px;'><div style='color: #e2e8f0; font-weight: 500; font-size: 0.85rem;'>{escape_html(f'{ev.get('signal_type', '').upper().replace('_', ' ')}')}</div><div style='color: {escape_html(f'{ev_color}')}; font-family: monospace; font-size: 0.8rem;'>Weight: {escape_html(f'{sign}')}{escape_html(f'{abs(ev.get('weight', 0.0)):.2f}')}</div><div style='color: #94a3b8; font-size: 0.8rem;'>{escape_html(f'{ev.get('note')}')}</div></div>")
                    
                st.html("<br><div style='font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 0.05em;'>ANALYST ACTIONS</div>")
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("Confirm Resolution", key=f"conf_{selected_rel_id}", width='stretch'):
                        update_edge_status(selected_rel_id, "confirmed")
                        st.rerun()
                with bc2:
                    if st.button("Reject Match", key=f"rej_{selected_rel_id}", width='stretch'):
                        update_edge_status(selected_rel_id, "rejected")
                        st.rerun()
