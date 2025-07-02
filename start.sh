#!/usr/bin/env bash

# Ensure script runs from its own directory
cd "$(dirname "$0")"
set -euo pipefail

# Activate virtual environment
source venv/bin/activate

# Ensure Gunicorn and Google GenAI SDK are installed
pip install gunicorn google-genai

# Kill any existing process on port 5000
if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:5000 | xargs -r kill -9 || true
fi

# Start the Flask app with Gunicorn
exec venv/bin/python -m gunicorn \
    --chdir "$(pwd)" \
    --pythonpath "$(pwd)" \
    --workers 3 \
    --bind 0.0.0.0:5000 \
    wsgi:application 