"""Loopback-only demo entrypoint; serves the built React app and existing API."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from backend.main import app
from backend.db import init_db, SessionLocal
from backend.services.workbench_seed import seed_workbench
from backend.services.workbench_security import require_session

DIST = Path(__file__).resolve().parents[1] / "frontend-react" / "dist"


@asynccontextmanager
async def demo_lifespan(app):
    init_db()
    with SessionLocal() as db:
        seed_workbench(db)
        from backend.services.workbench_library import seed_library
        seed_library(db)  # synthetic case library; before import so exact-IP correlation can see it
        from backend.data_sources.importer import import_datasets
        import_datasets(db)  # offline bundled snapshots only; idempotent
        from backend.models.entities import Persona
        if not db.query(Persona).first():
            from scripts.seed_demo import seed_database
            from backend.services.correlation_service import CorrelationService
            seed_database(db)
            CorrelationService.run_correlation(db)
    yield


app.router.lifespan_context = demo_lifespan


@app.middleware("http")
async def security_headers(request, call_next):
    if request.url.path.startswith('/api/v1/') and not request.url.path.startswith('/api/v1/workbench/') and request.method != 'OPTIONS':
        try:
            require_session(request)
        except HTTPException as exc:
            return JSONResponse({'detail': exc.detail}, status_code=exc.status_code, headers=exc.headers)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


if (DIST / "static").exists():
    app.mount("/static", StaticFiles(directory=DIST / "static"), name="app-assets")


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path.startswith(("api/", "static/")):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    if path in {"favicon.svg", "icons.svg", "workbench-mark.svg"} and (DIST / path).exists():
        return FileResponse(DIST / path)
    if not (DIST / "index.html").exists():
        return JSONResponse({"detail": "Build frontend-react first: npm ci && npm run build"}, status_code=503)
    return FileResponse(DIST / "index.html")
