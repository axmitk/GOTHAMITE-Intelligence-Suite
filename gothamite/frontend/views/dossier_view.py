from html import escape as escape_html
import streamlit as st
from frontend.api_client import get_persona_dossier

CARD = "background-color: #0f172a; padding: 20px; border: 1px solid #1e293b; margin-bottom: 20px;"


def render_dossier(graph_data):
    st.html('<h2>06 &mdash; INVESTIGATE / DOSSIER</h2>')
    st.html("<div style='color: #94a3b8; margin-bottom: 20px;'>Persona dossier: extracted identifiers, source artifacts and "
            "candidate cross-source linkages (NIST CSF Respond: RS.AN incident analysis). Synthetic corpus.</div>")
    st.markdown("---")

    nodes = graph_data.get("nodes", [])
    if not nodes:
        st.info("No personas available for a dossier.")
        return

    options = {f"{n.get('handle')} (source: {n.get('source_id', 'unknown')})": n for n in nodes}
    selected = st.selectbox("Persona", list(options.keys()))
    entity = options[selected]
    handle = entity.get('handle')

    api_dossier = get_persona_dossier(entity.get('id'))
    if not api_dossier:
        st.error("Dossier data could not be loaded from the backend.")
        return

    idents = api_dossier.get('identifiers', [])
    pgps = [i['value'] for i in idents if i['type'] == 'pgp_fingerprint']
    wallets = [i['value'] for i in idents if i['type'] == 'wallet']
    links = api_dossier.get('correlated_links', [])
    strongest = max(links, key=lambda l: l['score']) if links else None

    st.html(f"<h3>PERSONA DOSSIER: <span style='color: #38bdf8;'>{escape_html(f'{handle}')}</span></h3>")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.html('<h4>EXTRACTED IDENTIFIERS</h4>')
        rows = [
            ("Handle", handle),
            ("Source", api_dossier.get('source_id', 'unknown')),
            ("PGP fingerprints", "<br>".join(escape_html(p) for p in pgps) if pgps else "None extracted"),
            ("Wallet identifiers", "<br>".join(escape_html(w) for w in wallets) if wallets else "None extracted"),
            ("Candidate aliases", ", ".join(escape_html(l['target_handle']) for l in links) if links else "None proposed"),
        ]
        table = "".join(
            f"<tr><td style='padding: 8px 0; color: #64748b; width: 30%;'>{escape_html(k)}</td>"
            f"<td style='font-family: monospace; color: #f8fafc; word-break: break-all;'>{v if k in ('PGP fingerprints', 'Wallet identifiers', 'Candidate aliases') else escape_html(str(v))}</td></tr>"
            for k, v in rows)
        st.html(f"<div style='{CARD}'><table style='width: 100%; color: #cbd5e1; font-size: 0.9rem;'>{table}</table></div>")

        st.html('<h4>AUTOMATED INTERPRETATION (DETERMINISTIC)</h4>')
        if strongest:
            summary = (f"{len(idents)} identifiers extracted from source artifacts. {len(links)} candidate cross-source "
                       f"linkage{'' if len(links) == 1 else 's'}; the strongest is {strongest['target_handle']} ({strongest['target_source']}) at "
                       f"score {strongest['score']:.2f}, status {strongest['status']}. The score is a sum of documented evidence "
                       "weights, not a probability. Analyst review decides whether a linkage is accepted.")
        else:
            summary = (f"{len(idents)} identifiers extracted. Insufficient evidence for a cross-source linkage: "
                       "no shared PGP fingerprint, wallet or succession pattern was found.")
        st.html(f"<div style='{CARD}'><div style='color: #f8fafc; font-size: 0.9rem; line-height: 1.5;'>{escape_html(summary)}</div>"
                "<div style='color: #64748b; font-size: 0.75rem; margin-top: 8px;'>Rule-based summary of the evidence table. "
                "No language model is used in this build.</div></div>")

        st.html('<h4>SOURCE ARTIFACTS</h4>')
        obs_html = f"<div style='{CARD}'>"
        timeline = api_dossier.get('timeline', [])
        for t in timeline[:3]:
            obs_html += (
                "<div style='margin-bottom: 12px; border-bottom: 1px solid #1e293b; padding-bottom: 12px;'>"
                f"<div style='color: #94a3b8; font-size: 0.8rem; font-weight: 600; margin-bottom: 4px;'>SOURCE: {escape_html(str(api_dossier.get('source_id', 'unknown')))}</div>"
                f"<div style='color: #f8fafc; font-size: 0.9rem;'>{escape_html(str(t.get('snippet')))}</div>"
                f"<div style='color: #64748b; font-size: 0.75rem; margin-top: 4px; font-family: monospace;'>Collected: {escape_html(str(t.get('collected_at')))} | Artifact: {escape_html(str(t.get('artifact_id')))}</div>"
                "</div>")
        if not timeline:
            obs_html += "<div style='color: #64748b;'>No source artifacts recorded for this persona.</div>"
        st.html(obs_html + "</div>")

    with col2:
        st.html('<h4>STRONGEST CANDIDATE LINKAGE</h4>')
        score = f"{strongest['score']:.2f}" if strongest else "—"
        st.html(f"<div style='{CARD} text-align: center;'>"
                "<div style='color: #94a3b8; font-size: 0.8rem; font-weight: 600; letter-spacing: 0.1em; margin-bottom: 5px;'>LINKAGE SCORE</div>"
                f"<div style='color: #f8fafc; font-size: 2rem; font-family: monospace;'>{escape_html(score)}</div>"
                "<div style='color: #64748b; font-size: 0.75rem;'>Evidence-weight sum, capped at 0.95</div></div>")

        st.html('<h4>CANDIDATE LINKAGES</h4>')
        corr_html = "<div style='background-color: #0f172a; padding: 15px; border: 1px solid #1e293b;'>"
        for l in links:
            corr_html += (f"<div style='color: #cbd5e1; font-size: 0.85rem; margin-bottom: 8px;'>{escape_html(str(l['status']).upper())} · "
                          f"<b>{escape_html(str(l['target_handle']))}</b> ({escape_html(str(l['target_source']))}) · score {l['score']:.2f}</div>")
        if not links:
            corr_html += "<div style='color: #64748b; font-size: 0.85rem;'>No candidate linkages.</div>"
        st.html(corr_html + "</div>")
