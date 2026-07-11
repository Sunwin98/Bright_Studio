"""Headless server entry for the packaged app (no pywebview)."""
import argparse
import uvicorn
from app.main import app

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
