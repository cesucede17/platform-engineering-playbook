# Prompt: create a platform project

**Author:** CSUELA · **Date:** 2026-10-08

> **How to use this (human):** create an empty folder for the project, open Claude Code inside
> it, and type:
>
> ```text
> Read <PATH>\platform-engineering-playbook\NEW_PLATFORM_PROJECT_PROMPT.md and follow it to create the project in this folder.
> ```
>
> (`<PATH>` is wherever you have the `platform-engineering-playbook` folder). You need the
> personal pipeline (`general-pipeline/`) installed once, beforehand. Claude will explain what
> it's going to create, ask you some questions, install and verify the skills, propose a design,
> and build the structure. You just answer and approve.
>
> Everything below is addressed to Claude.

---

## Instructions for Claude

You're going to create a new **platform / web application** project in the current working
directory. `GUIDE` is the folder containing this file (`platform-engineering-playbook`). Follow
the phases **in order**. Each phase has a **gate**: don't move to the next one until it's met and
you've shown the evidence (command output) to the human.

### Rules for the whole process

- **Language and tone.** Reply in the profile's `language` (phase 0); so should the project's
  documentation and comments. Speak plainly and explain each technical term the first time it
  comes up, at the profile's `level`:
  - **low:** an everyday analogy and an example; short sentences; one step at a time;
  - **medium:** 1-2 sentences with an example;
  - **high:** only the unusual bits, in one sentence.
  Use generic examples ("an internal web app", "the team's shared server") unless the human
  gives you their own.
- **One question at a time.** If you have the `AskUserQuestion` tool, use it (at most 4 options,
  the recommended one first and labeled "(recommended)"; the tool adds "Other" on its own). For
  picking several things at once, use `multiSelect: true`. Without that tool, write numbered
  options and wait.
- **Nothing is installed or created without approval.** There are two explicit approvals: the
  interview summary (phase 2) and the design (phase 4).
- Read `GUIDE/PROJECT_GUIDE_PLATFORM.md` **before** phase 1: it's the structure and best-practices
  reference.
- Skills are chosen **only** via `GUIDE/tools/kit.py` from `GUIDE/SKILLS_CATALOG.json`. Don't
  install or enable plugins by hand, and don't add skills outside the catalog; if a new one is
  needed, propose it as a catalog change. **Every third-party skill goes through `skill-scanner`
  first.**
- **`security-guidance` is never activated on your own initiative** (the kit leaves it installed
  and disabled): only if the human explicitly asks. Don't `git push`.
- **`.env` is never read or printed**, nor any other secrets file — not with the file-reading
  tool, not with `cat`, not with `grep`, not any other way. To see which variables exist, use
  `.env.example`.
- **Shared servers** (the ones in the profile's `servers`): read-only, without coordination. No
  deploying, restarting, stopping, or changing anything on them unless the human has already
  notified whoever shares it (`shared_with`) and confirms it to you.
- **guardian is never bypassed.** The personal pipeline installed a watchdog (guardian) that can
  block one of your actions. If it does:
  1. stop and show the message;
  2. explain in one or two plain sentences, at the human's level, why that step is needed;
  3. if it's genuinely needed, ask the human to **manually** create the unlock file in the folder
     the message names (valid for 2 hours);
  4. once they confirm it's done, repeat the exact same action.
  Don't try to work around it — not with a script, not with an equivalent command. You never
  create that file yourself or write its name into a command. Quality-gate configs
  (`.pre-commit-config.yaml`, `tsconfig.json`, ESLint/Prettier config, the `[tool.ruff]`,
  `[tool.pytest]`, `[tool.mypy]` sections of `pyproject.toml`...) can be created, but not changed
  afterward: write them complete and correct the first time.
- Nothing is accepted without running it and seeing the output. If something fails, use
  `systematic-debugging` and fix the root cause — don't hide it or skip it.
- If the folder isn't empty, stop and ask before touching anything.
- If the project needs to train an ML model, that's a separate project (the
  `ml-engineering-playbook` kit): this platform will only load the already-validated model. Note
  it as a next step.

### How commands are written

- `PY` is the profile's Python launcher (`python` key: `python`, `python3`, or `py`).
- Write paths with `/` and in quotes, Windows included.

---

### Phase 0 — Check the personal pipeline and the environment

1. **Profile.** Read `~/.claude/pipeline_profile.json` with the file-reading tool (not a shell
   command).
   - **If it doesn't exist, stop here.** Explain, at the "low" level, that the personal pipeline
     comes first: it's installed once and sets up the watchdog, the startup summary, the journal,
     and tasks. Tell them the sentence: `Read <PATH>/general-pipeline/INSTALL_PROMPT.md and follow
     it`, and to retype this guide's sentence once done. Create nothing.
   - If it exists, keep `level`, `language`, `python` (this is `PY`), `roots`, and `servers`. If
     `format` is greater than 1, warn that the personal pipeline is newer than this guide, and
     continue.
   - If the current folder isn't inside any of the `roots`, flag it: the startup summary won't
     recognize it as a project. Let the human decide whether to continue here or move it.
2. **Environment.** Check (without installing anything) that these exist: `git`, `PY` (≥ 3.10),
   `uv`, `claude`, `docker`, `task` (go-task), `pre-commit`, and `gitleaks`, plus `node`/`npm` if
   there will be TypeScript or a front-end.

**Gate 0:** profile read (level, language, `PY`, and servers) + a tool → version / MISSING table.
If something essential is missing, say how to install it and wait. Anything that only affects
later steps gets noted and you move on.

---

### Phase 1 — Context brief: what's being created and why (short)

Explain it in your own words, at the human's `level`, in a few lines:

1. **What you're going to do:** some questions about the platform, installing and verifying the
   project's skills, designing the structure together, and checking that the container, tests,
   and CI work before the first commit.
2. **The structure:** by default, **a single application, cleanly split into modules** (like a
   building with independent floors: one can be renovated without touching the others); several
   applications only for a concrete reason. **Why:** it's the simplest to maintain, and splitting
   later is easy if the modules are well separated.
3. **The security rules** that will end up in the project's `CLAUDE.md`: the shared server is
   look-only, no deploying or restarting without telling whoever shares it, secrets (`.env`) are
   never read, and third-party skills are reviewed before installing.
4. End with "Shall we start?" and wait for the answer.

---

### Phase 2 — Interview: what the project needs

One question at a time. If the human doesn't know, suggest the recommended option and say so:
everything gets written into ADR 0001 and can be changed.

1. **Name**, **what it's for**, and **who uses it** (free text).
2. **Stack** (guide §1): Python/FastAPI back-end (recommended) · TypeScript/Node back-end · both.
   Then, if it has a web UI: React (recommended) · another (Vue...) · no UI.
3. **Modules:** what functional parts it has (free text; e.g. "users", "reports", "data upload").
   Propose a list yourself from what they've described and ask them to confirm it. Then: **one
   application** with those modules (modular monolith, recommended) · **several** (API + web +
   worker, or several tools). If they choose several, ask why: it goes into the ADR.
4. **Authentication:** OIDC with a provider (which one) · none (internal use, no sensitive data).
5. **Where it deploys:** Docker Compose on its own server (recommended) · Kubernetes · cloud.
6. **Shared server**, linked to the profile's `servers`:
   - If the profile has servers, show them (`hosts` and `shared_with`) and ask whether this
     platform will deploy or run on one of them: one of them · none · a different one.
   - If the profile has none, ask whether it will deploy on a server shared with other people:
     no (recommended if unsure) · yes.
   - If it's **a different one** or **yes** and it's not in the profile, ask for its name or IP
     and who it's shared with, and recommend re-running the personal pipeline guide afterward
     (question 2.4) so guardian protects it too. Meanwhile, the rule stays in the project's
     `CLAUDE.md`.
7. **Requirements → catalog options**, as `multiSelect` questions of up to 4 options each (check
   every one that applies; `api` always applies; stack ones already came from question 2):

| Question | Option |
|---|---|
| Python back-end? TypeScript / Node back-end? | `python`, `typescript` |
| Has a web UI? With React? | `front`, `react` |
| Relational database? | `db` |
| Uses LLMs (Claude's API or others), RAG, or prompts? | `llm` |
| Scheduled jobs with Airflow? Data > 50 GB? | `airflow`, `big_data` |
| Kubernetes? Terraform? | `k8s`, `iac` |
| Repository on GitLab or GitHub? | `gitlab` or `github` |
| Excel, Word, PowerPoint, or PDF as input or output? | `office` |

**Gate 2:** summary (name, stack, modules, one or several applications, authentication,
deployment, shared server, and options) and the exact `kit.py select` command you're about to
run. Wait for the human's "yes."

---

### Phase 3 — Install and verify the skills

From the project folder:

```bash
PY "GUIDE/tools/kit.py" select --type platform --options <opt1,opt2,...>
PY "GUIDE/tools/kit.py" install
```

`select` writes `.claude/pipeline-skills.json` (manifest: which skills this project uses and in
which phase), `.claude/settings.json` (the project's marketplaces and plugins; version-controlled
for the team), and copies local skills into `.claude/skills/`. `install` registers any missing
marketplaces and installs the plugins with `--scope project` (`security-guidance` stays
disabled).

Then:

1. Create a provisional `CLAUDE.md` with the project title and run
   `PY "GUIDE/tools/kit.py" table --write CLAUDE.md`.
2. Run `PY "GUIDE/tools/kit.py" check`. It must end in `OK` with exit code 0. If there are
   failures, run `install` again and diagnose what remains.
3. Ask the human to type **`/reload-plugins`** and wait for confirmation.
4. Verify **inside the session** that your available-skills list includes at least:
   `architecture-patterns`, `api-design-principles`, `brainstorming`, `writing-plans`,
   `test-driven-development`, `verification-before-completion`, and `security-review`, plus
   `frontend-design` if there's a `front`. If any is missing, stop and diagnose: don't continue
   without them.

**Gate 3:** `check` output is `OK` + confirmation that the skills are loaded in the session.

---

### Phase 4 — Design

Use the **`brainstorming`** skill, supported by **`architecture-patterns`**, to close with the
human on the guide's structure (§3.1 single application or §3.2 monorepo) adapted to their
answers: the modules from question 3 as domains, layers, which folders are extra or missing,
`task` commands, CI stages, environments, and deployment (and, if there's a shared server, how to
coordinate on it). Also close, following the guide:
- the one-primary-tool-per-phase table (§10);
- what goes into each level of automated gates (§11);
- if it's a monorepo, the module manifest, the contract, and the boundary (§12);
- the deployment procedure (§13). If it deploys to a server, the deployment tool and its rehearsal
  stay as a **task before the first real deployment**, not part of creation.
Write the spec in `docs/superpowers/specs/YYYY-MM-DD-initial-structure-design.md`,
`docs/adr/0001-project-structure.md`, and, with `/c4-architecture`, the C4 context-and-containers
diagram in `docs/architecture/`.

**Gate 4:** the human approves the spec in writing.

---

### Phase 5 — Plan and scaffold

1. With `writing-plans`, write the plan in `docs/superpowers/plans/` as small, verifiable tasks.
2. Execute the plan with TDD (`test-driven-development`), using the manifest's skills for each
   phase (`api-design-principles` for the contract, the Python/TypeScript ones for the code,
   `frontend-design` for the UI, `gitlab-ci-patterns` or `github-actions-templates` for CI).
3. The skeleton must include, at minimum:
   - The approved structure, with `.gitkeep` in empty folders.
   - Root files per guide §3.1: `README.md`, `CLAUDE.md` (guide §7 template, **with the
     "Server and security" section filled in** from question 6; the skills section **is not
     hand-written**: it's regenerated with `kit.py table --write CLAUDE.md`), `CONTRIBUTING.md`,
     `CHANGELOG.md`, `SECURITY.md`, `.editorconfig`, `.gitignore`, `.gitattributes`,
     `.env.example`, `.pre-commit-config.yaml` with the guide's two levels (§11) (level 1 on every
     commit; the message check, requiring that a `fix(<module>)` include the matching changelog
     entry for that module unless `No-changelog: <reason>`; level 2, tests + lint + types for
     what changed, at `pre-push`, which rejects the push if the ref being sent isn't `HEAD` or
     there are uncommitted changes), and an empty `docs/tech-debt.md` in §11's format — all
     written complete the first time.
   - In `CLAUDE.md`, the phase table with one primary tool and the "also, only if..." column
     (guide §10), right below the table the kit generates.
   - If it's a monorepo (guide §12): a manifest per module, `contract/CONTRACT.md` version 1,
     `docs/templates/CLAUDE_module.md`, and a per-module `CLAUDE.md` using that template; the
     cross-module boundary check at level 1; and a test that flags module folders with no
     manifest.
   - `Taskfile.yml` with the guide §3.3 commands (`setup`, `dev`, `test`, `lint`, `typecheck`,
     `build`, `migrate`, `ci`) plus **`skills`** (`PY scripts/verify_skills.py check`).
   - Copy `GUIDE/tools/kit.py` to `scripts/verify_skills.py` (its `check` and `table` subcommands
     work without the guide folder).
   - The CI file (`.gitlab-ci.yml` or `.github/workflows/ci.yml`) with the guide §4.6 stages.
   - Layered code with: config validated at startup, structured (JSON) logs, `/health` and
     `/ready`, an initial `docs/api/openapi.yaml`, and a contract test against it.
   - With `db`: an initial empty migration and `task migrate` working against the `compose.yml`
     database.
   - With `front`: a minimal landing page with its test and a basic accessibility check.
   - `infra/`: a multi-stage Dockerfile without a root user, and a `compose.yml` for the full
     local environment.
   - `docs/runbooks/deployment.md` with deploy and rollback per guide §13 (functional review, cold
     backup, deploy, health check, rollback); if there's a shared server, it starts with "notify
     `<shared_with>` and wait for confirmation."
   - If it deploys to a server: a pending task (in the plan or the human's task list) —
     "deployment tool (guide §13.2) and a rehearsal in an isolated Docker setup before the first
     real deployment."

Everything is tested **locally** (Docker on the developer's own machine). Nothing deploys to the
shared server during project creation.

---

### Phase 6 — Verify the pipelines work

Run each check and show its output. **All** that apply must pass:

| Check | When |
|---|---|
| `task skills` is `OK` (including `security-guidance` disabled) | always |
| `task ci` (lint + types + tests) is green | always |
| `pre-commit run --all-files` is green; a fake secret in a test file makes gitleaks fail | always |
| `pre-commit run --hook-stage pre-push --all-files` is green, and a deliberately broken test makes it fail (then reverted) | always |
| A deliberate cross-module import makes the boundary check fail (then reverted) | monorepo |
| The no-manifest-folder test passes and flags an empty module folder when created | monorepo |
| With the module served by path (`/<module>`), the full login flow ends inside the module, not at the portal | monorepo with portal + SSO |
| The CI file is valid YAML and its stages call the same `task` commands | always |
| `task build` + `docker compose up` locally: `/health` and `/ready` respond 200 | always |
| Contract test: the API matches `openapi.yaml` | always |
| The app doesn't start if a required environment variable is missing (automated test) | always |
| The image doesn't run as root (`docker run … id -u` ≠ 0) | always |
| `CLAUDE.md` has the "Server and security" section filled in | always |
| `task migrate` applies and reverts the initial migration | with `db` |
| Minimal browser e2e test (`webapp-testing`) | with `front` |
| `kubectl apply --dry-run=client` / `terraform validate` | with `k8s` / `iac` |

If something can't be run on this machine (e.g. no Docker), say so clearly and note it as
pending — don't mark it as passed.

**Gate 6:** every applicable row green, with its output.

---

### Phase 7 — Wrap-up

1. Review the full diff with `requesting-code-review` (or `/code-review`), and run
   `security-review` and `/audit` (insecure-defaults). Fix what comes up.
2. `git init` (`main` branch) if not done already, and a first commit `chore: initial structure`.
   No push.
3. Final report to the human:
   - Project tree (2 levels).
   - Skills-per-phase table (the one in `CLAUDE.md`).
   - Result of every phase-6 check.
   - Pending items (what couldn't be verified, and why).
   - Next step: the first feature, following the guide's §5 pipeline.
   - What's coming in a future guide version (guide §10, "Pending for a future version").
   - Reminder for the team: whoever clones the repo opens Claude Code, accepts the project's
     plugins, runs `/reload-plugins` and `task skills`; and protect `main` on GitLab/GitHub.

---

### Changing requirements later

```bash
PY "GUIDE/tools/kit.py" select --type platform --options <all options, old and new>
PY "GUIDE/tools/kit.py" install
PY "GUIDE/tools/kit.py" table --write CLAUDE.md
PY "GUIDE/tools/kit.py" check
```

then `/reload-plugins`. `select` doesn't disable plugins that were already enabled: if an option
is removed, the human reviews `.claude/settings.json` by hand (guardian doesn't let Claude edit
it).
