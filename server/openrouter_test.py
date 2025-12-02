# server/openrouter_test.py
from dotenv import load_dotenv
load_dotenv()
import os, json, requests

KEY = os.getenv("OPENROUTER_API_KEY")

resp = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "openai/gpt-4o-mini",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 16,
    },
    timeout=15,
)

print("status:", resp.status_code)
try:
    print(json.dumps(resp.json(), indent=2))
except Exception:
    print(resp.text)
