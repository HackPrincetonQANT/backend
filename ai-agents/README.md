# AI Agents

This folder hosts three agents for autonomous planning and execution:

- **Planner**: reads `planner/inputs/feature.md` + `lib/prompts/planner-system.txt` to generate `planner/plans/plan.md`
- **Executor**: reads `plan.md` and scaffolds minimal code files
- **Reviewer**: compares Figma screenshots to actual builds using Puppeteer visual diffs

## Quick Start

1. Clone this repo and run `cd ai-agents && npm install`
2. Fill out `planner/inputs/feature.md` with the feature you want to plan
3. Run:
   ```bash
   npm run plan
