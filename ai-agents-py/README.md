# AI Agents (Python)

This folder contains a **3-agent loop** in Python:

- **Planner**: reads `prompts/planner-system.txt` + `planner/inputs/feature.md`, writes `planner/plans/plan.md`
- **Executor**: parses `plan.md` and generates safe scaffolds/stubs
- **Reviewer**: screenshots a page and image-diffs vs. Figma PNG exports

---

## Run Locally

```bash
pip install -r requirements.txt
cp .env.example .env  # add your OpenAI key
python planner/plan.py
python executor/execute.py
python reviewer/review.py
```
---

## Artifacts

* **Planner** → `planner/plans/plan.md`
* **Reviewer** → `reviewer/artifacts/`


