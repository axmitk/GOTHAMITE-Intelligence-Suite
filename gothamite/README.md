# GOTHAMITE application

The current demo is the React investigation workbench. Start it from the release
repository with START_GOTHAMITE.ps1, or from this directory:

```powershell
.\.venv\Scripts\python.exe scripts/run_workbench.py
```

Open http://127.0.0.1:8042. Search **203.0.113.42** to begin the hero investigation.
See the [root README](../README.md) for setup, demo and limitations;
[architecture](../docs/ARCHITECTURE.md) for implementation decisions; and
[development log](../docs/OVERNIGHT_PROGRESS.md) for verification results.

## Legacy persona workbench

The original persona subsystem and Streamlit interface are retained. The React
shell links to its overview, graph, dossier and timeline pages. Dynamic HTML in
Streamlit views was migrated to sanitized st.html calls with escaped values.
Streamlit pages compute every figure from the loaded persona dataset; no model,
live collector or hardcoded result is displayed.
Python 3.12+ is required by formatting syntax; Streamlit 1.33+ by st.html.

To run Streamlit separately, use the original development backend on loopback:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --http h11 --loop asyncio
# Separate PowerShell terminal, same directory:
.\.venv\Scripts\python.exe -m streamlit run frontend/app.py
```

The original API entrypoint does not provide the demo server's legacy API session
guard. Keep it local. The new case workflows belong to the React demo entrypoint.
Historical design notes are under Docs; aspirational claims in older documents
should not be treated as implemented capabilities.
