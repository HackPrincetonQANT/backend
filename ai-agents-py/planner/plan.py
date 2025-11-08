from pathlib import Path
from lib.files import read_text, write_text
from lib.llm import chat_complete

SYSTEM_PATH = "ai-agents-py/prompts/planner-system.txt"
INPUT_PATH  = "ai-agents-py/planner/inputs/feature.md"
OUTPUT_PATH = "ai-agents-py/planner/plans/plan.md"

def main():
  system = read_text(SYSTEM_PATH)
  user   = read_text(INPUT_PATH)
  plan = chat_complete(system, user)
  write_text(OUTPUT_PATH, plan)
  print(f"✅ wrote {OUTPUT_PATH}")

if __name__ == "__main__":
  Path("ai-agents-py/planner/plans").mkdir(parents=True, exist_ok=True)
  main()
