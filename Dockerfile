# GOTHAMITE hosted demo: React build + FastAPI demo server in one container.
# The database lives in /tmp and is recreated from the bundled seed and dataset
# snapshots on every start, so each deploy/restart shows the canonical demo.

FROM node:22-slim AS frontend
WORKDIR /build
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
COPY gothamite/frontend-react/package.json gothamite/frontend-react/package-lock.json ./
# The Windows-only native bindings pinned for local development do not install on
# Linux; npm resolves the Linux bindings as optional dependencies instead.
RUN npm pkg delete "devDependencies.@oxlint/binding-win32-x64-msvc" "devDependencies.@rolldown/binding-win32-x64-msvc" \
 && npm install --no-audit --no-fund
COPY gothamite/frontend-react/ ./
RUN npm pkg delete "devDependencies.@oxlint/binding-win32-x64-msvc" "devDependencies.@rolldown/binding-win32-x64-msvc" \
 && npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 \
    GOTHAMITE_DB_PATH=/tmp/gothamite-demo.db PORT=10000
WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.100,<1" "uvicorn[standard]>=0.22,<1" "pydantic>=2,<3" \
    "sqlalchemy>=2,<3" "networkx>=3,<4" "Levenshtein>=0.23,<1" "python-dateutil>=2.8.2"
COPY gothamite/backend ./backend
COPY gothamite/scripts ./scripts
COPY --from=frontend /build/dist ./frontend-react/dist
RUN useradd --create-home app && chown -R app /app
USER app
EXPOSE 10000
CMD ["sh", "-c", "rm -f \"$GOTHAMITE_DB_PATH\" && exec uvicorn backend.demo:app --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips='*'"]
