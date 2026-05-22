"""
run.py – Entry point for Smart Traffic AI
Run from the project root:
  python run.py
  python run.py --host 0.0.0.0 --port 8080 --reload
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(description="Smart Traffic AI Server")
    parser.add_argument("--host",   default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port",   default=8000, type=int, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true",   help="Enable auto-reload for development")
    args = parser.parse_args()

    # Create output dirs
    for d in ("violations", "static/css", "static/js"):
        Path(d).mkdir(parents=True, exist_ok=True)

    try:
        import uvicorn
    except ImportError:
        print("❌  uvicorn not installed.  Run:  pip install uvicorn[standard]")
        sys.exit(1)

    print("""
╔══════════════════════════════════════════════════════════════╗
║         SMART TRAFFIC AI – COMMAND CENTER                   ║
║         Real-Time Helmet & Seatbelt Detection               ║
╚══════════════════════════════════════════════════════════════╝
""")
    print(f"  🌐  Dashboard  : http://{args.host}:{args.port}")
    print(f"  📡  API Docs   : http://{args.host}:{args.port}/docs")
    print(f"  🔌  WebSocket  : ws://{args.host}:{args.port}/ws")
    print()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
