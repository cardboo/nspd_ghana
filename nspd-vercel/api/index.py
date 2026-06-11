"""
Vercel serverless entrypoint.

@vercel/python detects the ASGI `app` object and serves it. All /api/*
requests are routed here by vercel.json.
"""

import sys
from pathlib import Path

# Make the project root importable so `backend` resolves inside the lambda.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app  # noqa: E402,F401
