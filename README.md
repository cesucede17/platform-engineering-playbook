# Platform Engineering Playbook

A kit for creating platform / web application projects **with a single prompt**: Claude Code
asks what the project needs, installs and verifies the right skills, designs the structure
following best practices, and checks that the pipelines actually run before the first commit.

This folder is **self-contained**: share it as-is, and it only needs the companion
[personal pipeline guide](general-pipeline/README.md) installed once.

## Prerequisite: the personal pipeline

This guide requires the **personal pipeline** ([`general-pipeline/`](general-pipeline/README.md))
to be installed once per person (the guardian watchdog, the startup summary, the journal and
tasks). The prompt checks this by reading `~/.claude/pipeline_profile.json`; if it's missing, it
stops and tells you how to install it. That profile also provides your experience level (how much
Claude explains), your language, and any shared servers you declared.

## Project safety rules

Every generated project's `CLAUDE.md` carries these rules:

- any **shared server** is **read-only** without coordination;
- **no deploys or restarts** on it without notifying whoever shares it first;
- **`.env` is never read or printed**;
- every **third-party skill** goes through **`skill-scanner`** first;
- **`security-guidance`** is never activated on Claude's own initiative, only on request.

## How to create a project

1. Create an empty folder for the project and open Claude Code inside it.
2. Type:

   ```text
   Read <PATH>/platform-engineering-playbook/NEW_PLATFORM_PROJECT_PROMPT.md and follow it to create the project in this folder.
   ```

3. Answer the questions, type `/reload-plugins` when Claude asks you to, and approve the design.

| Phase | What happens | How it's checked |
|---|---|---|
| 0. Profile and environment | Checks the personal pipeline is installed and what tools you have | Profile read + tool → version table |
| 1. Context brief | Explains briefly what will be created and why | You say "let's start" |
| 2. Interview | Stack, modules, authentication, deployment, shared server, and requirements | You approve the summary |
| 3. Skills | `kit.py` selects, installs, and verifies the skills | `kit.py check` passes + skills loaded in session |
| 4. Design | `brainstorming` on the adapted guide structure | You approve the spec |
| 5. Structure | Plan + skeleton with TDD, CI, pre-commit, `task skills` | — |
| 6. Verification | End-to-end pipelines, locally (see phase 6 of the prompt) | Output of every command |
| 7. Wrap-up | Review, first commit (no push), report | Final report |

## Contents

```
platform-engineering-playbook/
├── README.md                              This file
├── NEW_PLATFORM_PROJECT_PROMPT.md         THE prompt: what gets asked of Claude
├── PROJECT_GUIDE_PLATFORM.md              Reference: structure and best practices
├── SKILLS_CATALOG.json                    Single source of truth for skills: plugin, phase, when each installs
├── tools/kit.py                           Selects, installs, and checks skills (plain Python, no dependencies)
└── vendored_skills/                       Third-party skills, with LICENSE and .upstream-commit
```

Vendored skills included: `composition-patterns`, `find-bugs`, `react-best-practices`,
`security-audit`, `security-review`, `skill-scanner` — from
[getsentry/skills](https://github.com/getsentry/skills) (Apache-2.0) and
[vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills) (MIT), redistributed as-is
with their original license and attribution — not authored by me.

## Options the kit understands

| Option | Meaning |
|---|---|
| `python` | Python codebase |
| `typescript` | TypeScript / Node codebase |
| `front` | Has a web UI |
| `react` | The UI uses React |
| `api` | Exposes an HTTP API |
| `db` | Relational database with migrations |
| `llm` | Uses LLMs (Claude's API or others), RAG, or prompts |
| `airflow` | Orchestration with Airflow |
| `big_data` | Large datasets (> 50 GB), Spark |
| `k8s` | Kubernetes deployment |
| `iac` | Infrastructure as code (Terraform) |
| `gitlab` | Repository and CI on GitLab |
| `github` | Repository and CI on GitHub |
| `office` | Reads or writes Excel, Word, PowerPoint, or PDF |

## How pipeline skills are kept working

- **One source of truth:** `SKILLS_CATALOG.json` states which skill, agent, or command is used,
  which plugin it comes from, in which phase, and for which requirements. No one picks skills by hand.
- **Reproducible selection:** `kit.py select` generates `.claude/settings.json` (version-controlled,
  so cloning the repo gives everyone the same plugins) and `.claude/pipeline-skills.json` (the
  project's manifest).
- **Project-scoped install:** `kit.py install` registers marketplaces and installs with `--scope project`.
- **Real verification:** `kit.py check` confirms via `claude plugin list` that every plugin is
  installed for that folder in the right state, that every skill/agent/command exists inside its
  plugin, that local skills carry a license and provenance, and that the skills table in
  `CLAUDE.md` matches the manifest.
- **Inside the project:** the kit ships as `scripts/verify_skills.py` and is checked with `task skills`.

### Adding requirements later

```bash
python <PATH>/platform-engineering-playbook/tools/kit.py select --type platform --options <all, old and new>
python <PATH>/platform-engineering-playbook/tools/kit.py install
python <PATH>/platform-engineering-playbook/tools/kit.py table --write CLAUDE.md
python <PATH>/platform-engineering-playbook/tools/kit.py check
```

and `/reload-plugins` in Claude Code.

## Platform patterns

`PROJECT_GUIDE_PLATFORM.md` describes, from §10 onward, four patterns drawn from a real
production platform. The prompt applies them when creating the project, adapted to the interview:

- **§10, plugin map:** one primary tool per phase; surplus plugins are disabled at project scope.
- **§11, automated gates:** level 1 on every commit, level 2 on every push. Exceptions are logged
  in `docs/tech-debt.md`.
- **§12, module structure:** a manifest, a versioned contract, a verified boundary, and a template
  `CLAUDE.md` per module.
- **§13, deployment:** functional review, isolated rehearsal, cold backup, deploy and rollback,
  with rules drawn from real incidents.

The deployment tool itself isn't packaged: each project builds it around its own volumes and
modules, following §13.2, before its first real deployment.

## What if there's also an ML model to train?

That's a separate project, using the `ml-engineering-playbook` kit.

## Maintaining the kit

- **Adding or changing a skill:** edit `SKILLS_CATALOG.json`. A new third-party skill goes through
  `skill-scanner` first and is stored in `vendored_skills/` with `LICENSE` and `.upstream-commit`.
- **Updating a vendored skill:** re-copy it from the source repo, run `skill-scanner`, and update
  `.upstream-commit`.
- `tools/kit.py` is identical in `ml-engineering-playbook` and `platform-engineering-playbook`: if
  changed in one, copy it to the other.
