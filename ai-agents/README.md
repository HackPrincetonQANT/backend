# AI Agents (Python)

This folder contains a 3-agent loop in Python:

- **Planner**: reads `prompts/planner-system.txt` + `planner/inputs/feature.md`, writes `planner/plans/plan.md`
- **Executor**: parses `plan.md` and generates safe scaffolds/stubs
- **Reviewer**: screenshots a page and image-diffs vs. Figma PNG exports

## Run locally
