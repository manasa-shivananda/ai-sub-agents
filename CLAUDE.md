# CLAUDE.md

## gstack

Installed at `~/.claude/skills/gstack`. Available skills:

- `/gstack` — Headless browser for QA testing, site dogfooding, screenshots, and bug evidence
- `/autoplan` — Auto-generate implementation plans
- `/benchmark` — Run benchmarks
- `/browse` — Browse and interact with web pages
- `/canary` — Canary deployment checks
- `/careful` — Extra-careful mode for sensitive changes
- `/checkpoint` — Create checkpoints for safe rollback
- `/codex` — Code generation and transformation
- `/connect-chrome` — Connect to a running Chrome instance
- `/cso` — Chief of Staff Operations — executive-level planning
- `/design-consultation` — Design consultation and feedback
- `/design-html` — Generate HTML designs
- `/design-review` — Review designs
- `/design-shotgun` — Rapid design iteration
- `/document-release` — Document a release
- `/freeze` — Freeze deployments
- `/gstack-upgrade` — Upgrade gstack to latest version
- `/guard` — Guard mode for safe operations
- `/health` — Health checks
- `/investigate` — Investigate issues and bugs
- `/land-and-deploy` — Land PRs and deploy
- `/learn` — Save learnings for future sessions
- `/office-hours` — Office hours mode
- `/plan-ceo-review` — CEO-level plan review
- `/plan-design-review` — Design plan review
- `/plan-eng-review` — Engineering plan review
- `/qa` — QA testing flows
- `/qa-only` — QA testing only (no fixes)
- `/retro` — Retrospective analysis
- `/review` — Code review
- `/setup-browser-cookies` — Set up browser cookies for authenticated testing
- `/setup-deploy` — Set up deployment configuration
- `/ship` — Ship code end-to-end (plan, implement, test, deploy)
- `/unfreeze` — Unfreeze deployments

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
