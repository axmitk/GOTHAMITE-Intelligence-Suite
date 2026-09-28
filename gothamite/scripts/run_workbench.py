"""Start the local, single-process synthetic workbench with stable DB location."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("GOTHAMITE_DB_PATH", str(ROOT / "workbench-demo.db"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.demo:app", host="127.0.0.1", port=int(os.getenv("GOTHAMITE_PORT", "8042")), proxy_headers=False, http="h11", loop="asyncio")
