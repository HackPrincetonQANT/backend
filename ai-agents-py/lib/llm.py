import os, requests
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def chat_complete(system: str, user: str, temperature: float = 0.2) -> str:
  if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY in .env")
  payload = {
    "model": OPENAI_MODEL,
    "temperature": temperature,
    "messages": [
      {"role": "system", "content": system},
      {"role": "user", "content": user}
    ]
  }
  r = requests.post(OPENAI_URL, json=payload, headers={
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
  }, timeout=120)
  r.raise_for_status()
  data = r.json()
  return data["choices"][0]["message"]["content"]
