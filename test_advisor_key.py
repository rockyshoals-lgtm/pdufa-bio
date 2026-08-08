#!/usr/bin/env python3
"""Quick test to verify your AI Advisor API key works before running the daemon."""
import os, sys, json, urllib.request
from pathlib import Path

def load_key():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in open(env_path).read().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                if "PERPLEXITY" in k or "PPLX" in k or "ANTHROPIC" in k:
                    return k.strip(), v.strip().strip('"').strip("'")
    return None, None

key_name, key = load_key()
if not key:
    print("❌ No API key found in .env")
    sys.exit(1)

print(f"Found key: {key_name}={key[:12]}...")

if "ANTHROPIC" in key_name:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 30,
        "messages": [{"role": "user", "content": "Say exactly: ODIN ONLINE"}]
    }
else:
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "max_tokens": 30,
        "messages": [{"role": "user", "content": "Say exactly: ODIN ONLINE"}]
    }

data = json.dumps(payload).encode()
req = urllib.request.Request(url, data=data, method="POST", headers=headers)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if "ANTHROPIC" in key_name:
            content = result["content"][0]["text"]
        else:
            content = result["choices"][0]["message"]["content"]
        print(f"✅ API key is VALID! Response: {content}")
except urllib.error.HTTPError as e:
    body = e.read().decode()[:200]
    if e.code == 401:
        print(f"❌ API key INVALID (401 Unauthorized)")
        print(f"   Go to perplexity.ai/settings/api and generate a new key")
        print(f"   Or get an Anthropic key at console.anthropic.com")
    elif e.code == 429:
        print(f"✅ Key appears VALID but rate-limited (429). Safe to proceed.")
    else:
        print(f"❌ HTTP {e.code}: {body}")
except Exception as e:
    print(f"❌ Connection failed: {type(e).__name__}: {e}")
