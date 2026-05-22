#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
#  Smart Traffic AI – One-shot installer
#  Usage:  bash install.sh
# ═══════════════════════════════════════════════════════════════

set -e

PYTHON=${PYTHON:-python3}

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         SMART TRAFFIC AI – INSTALLER                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Python check ──────────────────────────────────────────────────────────────
if ! command -v $PYTHON &>/dev/null; then
  echo "❌  Python not found. Install Python 3.10+ and retry."
  exit 1
fi
PYVER=$($PYTHON --version 2>&1 | awk '{print $2}')
echo "✅  Python $PYVER detected"

# ── Virtual environment ───────────────────────────────────────────────────────
if [ ! -d "venv" ]; then
  echo "🔧  Creating virtual environment…"
  $PYTHON -m venv venv
fi

# Activate
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi
echo "✅  Virtual environment activated"

# ── Upgrade pip ───────────────────────────────────────────────────────────────
pip install --upgrade pip --quiet

# ── Install requirements ──────────────────────────────────────────────────────
echo "📦  Installing dependencies (this may take a few minutes)…"
pip install -r requirements.txt

# ── Create directories ────────────────────────────────────────────────────────
mkdir -p violations static/css static/js

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  ✅  Installation complete!                                  ║"
echo "║                                                              ║"
echo "║  Start the system:                                           ║"
echo "║    python run.py                                             ║"
echo "║                                                              ║"
echo "║  Demo mode (no camera):                                      ║"
echo "║    python app/detection/run_detector.py --demo               ║"
echo "║                                                              ║"
echo "║  Dashboard: http://127.0.0.1:8000                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
