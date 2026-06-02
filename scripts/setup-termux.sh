#!/bin/bash
# Sift - One-click setup for Termux (Android)
set -e

# Always run from project root (parent of scripts/)
cd "$(dirname "$0")/.."

echo "=== Sift Setup ==="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Installing Python..."
    pkg install python -y 2>/dev/null || apt install python3 -y 2>/dev/null || {
        echo "ERROR: Cannot install Python. Run: pkg install python"
        exit 1
    }
fi

echo "Python: $(python3 --version)"

# Create venv
python3 -m venv .venv 2>/dev/null || {
    echo "Creating venv with --without-pip..."
    python3 -m venv --without-pip .venv
    .venv/bin/python3 -m ensurepip 2>/dev/null || true
}

# Install dependencies
echo "Installing dependencies..."
.venv/bin/pip install -r requirements.txt 2>/dev/null || \
.venv/bin/python3 -m pip install -r requirements.txt

# Create knowledge directory
mkdir -p knowledge

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> Please edit .env with your credentials <<<"
    echo "  1. API_KEY      - Your LLM API key"
    echo "  2. API_BASE_URL - Your LLM API endpoint"
    echo "  3. SMTP_AUTH_CODE - QQ mailbox authorization code"
    echo ""
fi

# Setup cron (Termux)
echo "Setting up cron..."
CRON_CMD="cd $(pwd) && .venv/bin/python3 sift/cli.py run >> output/cron.log 2>&1"

if command -v crond &>/dev/null || command -v crontab &>/dev/null; then
    # Termux uses crond, needs to be started
    (crontab -l 2>/dev/null; echo "0 8 * * 1 $CRON_CMD") | sort -u | crontab -
    echo "Cron job added: every Monday 08:00"
    echo "Start cron daemon: crond"
else
    echo "Cron not available. Install with: pkg install cron"
    echo "Manual run: .venv/bin/python3 sift/cli.py run"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Quick start:"
echo "  1. Edit .env with your credentials"
echo "  2. Run: .venv/bin/python3 sift/cli.py run"
echo ""
echo "Auto mode (every Monday 8am):"
echo "  crond  # start cron daemon"
