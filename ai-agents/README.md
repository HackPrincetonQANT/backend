# AI Agents

This folder hosts three agents for autonomous planning and execution:

- **Planner** — reads `planner/inputs/feature.md` + `lib/prompts/planner-system.txt` to generate `planner/plans/plan.md`
- **Executor** — reads `plan.md` and scaffolds minimal code files
- **Reviewer** — compares Figma screenshots to actual builds using Puppeteer visual diffs

## Quick Start

1. Clone this repo and run:

   `cd ai-agents && npm install`

2. Fill out `planner/inputs/feature.md` with the feature you want to plan.  
3. Run:

   `npm run plan`

   This will output `planner/plans/plan.md`.

4. Optionally, run:

   `npm run exec`  
   `npm run review`

The `lib/prompts/` folder holds all the reusable system prompts that define each agent’s behavior.
