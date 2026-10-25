#!/usr/bin/env python3
"""
test_ollama_connection.py — Diagnostics tool for local Ollama LLM integration.

Usage:
    cd backend
    python test_ollama_connection.py
"""

import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

print(f"Checking Ollama connection at: {OLLAMA_BASE_URL}")
print(f"Target model: {OLLAMA_MODEL}")

try:
    resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
    if resp.status_code != 200:
        print(f"[FAIL] Ollama API returned HTTP status {resp.status_code}")
        sys.exit(1)

    data = resp.json()
    models = [m.get("name", "") for m in data.get("models", [])]
    model_names_only = [m.split(":")[0] for m in models]

    print(f"[OK] Ollama is running! Available models: {', '.join(models) if models else 'None'}")

    if OLLAMA_MODEL not in model_names_only and f"{OLLAMA_MODEL}:latest" not in models:
        print(f"[WARN] Target model '{OLLAMA_MODEL}' is not pulled yet.")
        print(f"  Fix: run  ollama pull {OLLAMA_MODEL}")
        sys.exit(1)

    print(f"[OK] Model '{OLLAMA_MODEL}' is available.")

    # Test minimal generation
    print("[...] Testing simple generation prompt with Ollama...")
    gen_resp = httpx.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": "Reply with exactly: HELLO", "stream": False},
        timeout=30.0,
    )
    if gen_resp.status_code == 200:
        text = gen_resp.json().get("response", "").strip()
        print(f"[OK] Generation succeeded! Output: {text!r}")
        print("\n=== Ollama integration is fully functional! ===")
    else:
        print(f"[FAIL] Ollama generation failed with status {gen_resp.status_code}: {gen_resp.text}")
        sys.exit(1)

except httpx.ConnectError:
    print(f"\n[FAIL] Cannot connect to Ollama at {OLLAMA_BASE_URL}.")
    print("  Fix: Is Ollama installed and running? Run: ollama serve")
    sys.exit(1)
except Exception as e:
    print(f"\n[FAIL] Unexpected error: {e}")
    sys.exit(1)
