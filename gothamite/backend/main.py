from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.db import init_db
from backend.api.ingest import router as ingest_router
from backend.api.correlate import router as correlate_router
from backend.api.graph import router as graph_router
from backend.api.entities import router as entities_router
from backend.api.artifacts import router as artifacts_router
from backend.api.export import router as export_router
from backend.api.workbench import router as workbench_router, session_router
from backend.services.workbench_security import ORIGINS, PUBLIC_HOST
from fastapi.middleware.trustedhost import TrustedHostMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema on startup
    init_db()
    yield


app = FastAPI(
    title="GOTHAMITE Threat Intelligence API",
    description="Cross-Source Dark Web Threat Actor Correlation & De-Anonymization Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"] + ([PUBLIC_HOST] if PUBLIC_HOST else []))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Transforms FastAPI/Pydantic 422 errors into standard 400 Bad Request responses
    per API_CONTRACT.md requirement: { "accepted": false, "errors": [...] }
    """
    error_messages = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "validation error")
        error_messages.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"accepted": False, "errors": error_messages},
    )


# Mount API Routers
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(correlate_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(workbench_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "GOTHAMITE API"}
