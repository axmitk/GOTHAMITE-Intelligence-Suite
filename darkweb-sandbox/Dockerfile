# One image for every sandbox service -- Phase 1 and the Phase-4 mock sites.
# Each compose service supplies its own command; the code and dependencies are
# identical across them.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/ ./common/
COPY directory/ ./directory/
COPY relay/ ./relay/
COPY client/ ./client/
COPY phase1_endpoint/ ./phase1_endpoint/
COPY mock_sites/ ./mock_sites/

# Relays generate their keypairs in memory at startup and never write them
# anywhere, so nothing here needs write access to the filesystem.
RUN useradd --create-home --uid 10001 sandbox
USER sandbox
