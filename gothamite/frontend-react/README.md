# GOTHAMITE frontend

React 18 + TypeScript + Vite + D3. The investigation workbench lives in
`src/workbench/`; the legacy persona pages (`/overview`, `/graph`, `/dossier`,
`/timeline`) live in `src/pages/`.

```powershell
npm run build       # production bundle served by the backend on 127.0.0.1:8042
npm run lint        # oxlint; 6 known warnings in legacy src/pages and src/components
npm run test:e2e    # 12 Playwright checks in installed Edge, temporary DB, port 8043
npm run dev         # hot reload on 5173, proxies the API to 8042
```

Screenshots and an example report from `test:e2e` go to `../verification/`.
Set `GOTHAMITE_BROWSER=chrome` to use Chrome instead of Edge. See the
[root README](../../README.md) for setup, the demo path and data provenance.
