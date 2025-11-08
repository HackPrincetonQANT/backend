from pathlib import Path

def read_text(p: str) -> str:
  return Path(p).read_text(encoding="utf-8")

def write_text(p: str, s: str):
  path = Path(p)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(s, encoding="utf-8")
