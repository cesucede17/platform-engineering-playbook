# Guide — Creating a platform development project

**Author:** CSUELA · **Date:** 2026-10-08

> **What it's for:** setting up a platform or web application (API, UI, background processes)
> from scratch, following recognized software-engineering best practices, with the same
> structure and the same Claude skills across the whole team.
> **How to use it:** no need to follow it by hand. In an empty folder, open Claude Code and ask
> it to read and follow `platform-engineering-playbook/NEW_PLATFORM_PROJECT_PROMPT.md`. This
> guide is the reference Claude (and the team) uses for structure and best practices.
> **Requirement:** the personal pipeline (`general-pipeline`) must already be installed, once
> per person. The prompt checks this and stops with a message if it's missing.
> **What it's built on:** The Twelve-Factor App, OWASP (Top 10 and ASVS), Conventional Commits,
> SemVer, Keep a Changelog, ADRs, the C4 model, the test pyramid, OpenTelemetry, and WCAG 2.1.

---

## 1. Before starting: the questions

Claude doesn't generate code until it has these answers (or an explicit assumption, written into
ADR 0001).

| Question | Usual options | What it changes |
|---|---|---|
| How many deployable applications? | **One** (modular monolith) · **several** (API + web + worker, or several tools) | One: application structure at the root. Several: monorepo with `apps/` and `packages/` |
| Stack? | Python (FastAPI) · TypeScript (Node/Express, NestJS) · React/Vue + Vite front-end | Language skills, lint and type tools |
| What modules does it have? | The functional parts: users, reports, data upload... | Domains inside `src/<app>/` (or the monorepo's apps) |
| Shared server? | One of the personal pipeline profile's `servers` · none · another | The `CLAUDE.md`'s "Server and security" section and the deployment runbook |
| Database? | PostgreSQL · SQLite (prototypes only) · none | Migrations, volumes, backups |
| Users and authentication? | OIDC with a provider (Keycloak, Entra ID, Auth0...) · none (internal use, no sensitive data) | Authentication/authorization layer, security review |
| Where does it deploy? | Docker Compose on its own server · Kubernetes · PaaS/cloud | `infra/` folder, CD pipeline |
| Repository and CI? | GitLab · GitHub | `.gitlab-ci.yml` or `.github/workflows/` |
| Personal or sensitive data? | Yes · No | GDPR, encryption, retention, mandatory threat model |
| Uses an LLM (Claude's API or another)? | Yes · No | `claude-api` skill, cost controls, prompt-injection defenses |

**Default rule:** start with **one modular monolith**, cleanly split by domain. Only split into
services when there's a concrete reason (different scaling needs, different teams, different
lifecycle), and that reason goes into an ADR.

---

## 2. Installing the skills

**Not installed by hand.** The `NEW_PLATFORM_PROJECT_PROMPT.md` prompt does it via
`tools/kit.py`, which picks skills from `SKILLS_CATALOG.json` based on the project's requirements
(options like `api`, `front`, `llm`, `gitlab`...), writes `.claude/settings.json` and
`.claude/pipeline-skills.json`, installs the plugins **at project scope**, and **verifies** that
every skill, agent, and command exists and is active. The project's phase → skills table lives
in its `CLAUDE.md` and is validated with `task skills`.

To preview what would happen without creating anything yet, in a test folder:

```bash
python <platform-engineering-playbook>/tools/kit.py select --type platform --options python,front,react,db,gitlab
python <platform-engineering-playbook>/tools/kit.py table
```

### `security-guidance`: installed but disabled

It reviews every turn with an LLM and burns a lot of tokens. The kit installs it disabled; it's
turned on deliberately for sensitive work, **only when the human asks** (Claude never enables it
on its own), and turned off again afterward:

```bash
claude plugin enable  security-guidance@claude-plugins-official --scope project   # then /reload-plugins
claude plugin disable security-guidance@claude-plugins-official --scope project
```

### Third-party skills

The vendored ones (`platform-engineering-playbook/vendored_skills/`) carry `LICENSE` and
`.upstream-commit`; the kit checks they're present. Before adding a new one to the catalog: run
`skill-scanner` on it and check whether it brings hooks, MCP servers, or scripts.

---

## 3. The structure

### 3.1 Single application (modular monolith)

```
<project>/
├── README.md               What it is, requirements, how to run/test/deploy
├── CLAUDE.md               Rules for Claude (template in §7)
├── CONTRIBUTING.md         Branching, commits, review, definition of done
├── CHANGELOG.md            Keep a Changelog; "Unreleased" section at the top
├── SECURITY.md             How to report vulnerabilities, and to whom
├── .editorconfig           Indentation, line endings, encoding
├── .gitignore              .env, data, build artifacts, .venv/, node_modules/, tmp/
├── .gitattributes          LF for text; binaries flagged
├── .pre-commit-config.yaml Format, lint, secrets, large files
├── .env.example            ALL variables, no real values, commented
├── Taskfile.yml            Standard commands (§3.3). A Makefile works too
├── .gitlab-ci.yml          (or .github/workflows/) CI/CD pipeline (§4.6)
├── .claude/                settings.json + skills/
│
├── src/<app>/
│   ├── domain/             Entities and business rules. No framework dependencies
│   ├── application/        Use cases: orchestrate the domain
│   ├── infrastructure/     DB, external APIs, files, queues (implement domain interfaces)
│   ├── interfaces/         Entry points: api/ (HTTP routes), cli/, workers/
│   └── config.py           Loads and validates config from environment variables
│
├── web/                    (if there's a front-end) src/, public/, tests next to components
├── migrations/             Versioned DB migrations (Alembic, Prisma, Flyway...)
│
├── tests/
│   ├── unit/               Fast, no network or DB. Mirrors src/'s tree
│   ├── integration/        Against a real DB in a container (Testcontainers or a test compose)
│   ├── contract/           The API matches its OpenAPI spec
│   ├── e2e/                Browser user journeys (Playwright)
│   └── fixtures/           Synthetic data. Never real data
│
├── infra/
│   ├── docker/             Multi-stage Dockerfile(s)
│   ├── compose.yml         Full local environment
│   ├── compose.prod.yml    Production differences
│   └── iac/                (if applicable) Terraform / Ansible / Kubernetes manifests
│
├── docs/
│   ├── architecture/       C4 diagrams: context, containers, components
│   ├── adr/                0000-template.md, NNNN-title.md. Never deleted: "superseded by"
│   ├── api/                openapi.yaml (the API's source of truth)
│   ├── runbooks/           Deploy, rollback, backup and restore, incidents
│   ├── security/           Threat model, audit reports
│   ├── superpowers/specs/  Designs: YYYY-MM-DD-<topic>-design.md
│   ├── superpowers/plans/  Implementation plans
│   └── journal/            End-of-day summaries
│
├── scripts/                One-off utilities (data seeding, maintenance)
└── tmp/                    Test runs and working copies. Ignored by git
```

### 3.2 Several applications (monorepo)

Same root as §3.1, but the code is split like this:

```
├── apps/                   Everything that deploys separately
│   ├── api/                With §3.1's internal shape (src/, tests/, migrations/, Dockerfile...)
│   ├── web/
│   └── worker/
├── packages/               Shared code: generated API client, types, common UI, utilities
│   └── <package>/          With its own version, tests, and README
```

Monorepo rules:
- Every app has its own `README.md`, `CLAUDE.md`, `CHANGELOG.md`, `Taskfile.yml`, `Dockerfile`,
  and `.env.example`, and builds, tests, and runs on its own from its folder.
- **An app never imports from another app.** Shared code goes into `packages/`, with a stable
  interface.
- Communication between apps happens through explicit, versioned contracts (OpenAPI, schema'd
  events).
- CI only builds and tests what changed (and whatever depends on it).

### 3.3 Standard commands

Every app implements the same names in its `Taskfile.yml` (or `Makefile`), so anyone can work on
any project:

| Command | What it does |
|---|---|
| `task setup` | Installs dependencies and pre-commit hooks |
| `task dev` | Runs locally with reload |
| `task test` | All tests |
| `task lint` / `task format` | Lint and format |
| `task typecheck` | Type checking |
| `task build` | Builds the Docker image |
| `task migrate` | Applies migrations |
| `task ci` | The same thing CI runs, locally |

---

## 4. Best practices (mandatory)

### 4.1 Architecture

- **Layers with dependencies pointing inward:** `interfaces → application → domain`;
  `infrastructure` implements interfaces defined by the domain. The domain knows nothing about
  the framework or the DB.
- **API-first:** `docs/api/openapi.yaml` is written or updated before the code; contract tests
  check the implementation matches it.
- **API versioning** (`/api/v1/...`); breaking changes go into a new version.
- **Architecture decisions as ADRs** (context, decision, alternatives discarded, consequences).
- **C4 diagrams** of context and containers in `docs/architecture/`, updated as they change.

### 4.2 Twelve-Factor (the essentials)

- **Configuration only via environment variables**, validated at startup (fail fast if something
  is missing).
- **Stateless processes:** state lives in the DB, a cache, or object storage — never on the
  container's disk.
- **Declared and locked dependencies** (`uv.lock`, `package-lock.json`).
- **Dev/prod parity:** the same services (same DB, same version) locally, in staging, and in
  production.
- **Logs to stdout**; the environment handles collecting them.
- **Fast startup and clean shutdown** (handle SIGTERM, close connections).

### 4.3 Code quality

- Automatic format and lint: **ruff** (Python), **ESLint or oxlint + Prettier** (TS).
- Strict types: **mypy or pyright** (Python), `"strict": true` in `tsconfig` (TS).
- Small functions, clear names, no dead or commented-out code.
- Errors handled explicitly: no `except: pass`; domain errors with their own type.
- Dependencies reviewed and updated regularly (Renovate or Dependabot).

### 4.4 Git and versioning

- `main` is protected and **always deployable**. No direct pushes.
- **Short-lived branches** (hours or a few days): `feat/<topic>`, `fix/<topic>`,
  `chore/<topic>`. Work in a worktree.
- **Conventional Commits:** `type(scope): description`. Types: `feat`, `fix`, `refactor`,
  `perf`, `docs`, `test`, `build`, `ci`, `chore`, `security`.
- **Small merge requests**, with at least one review and CI green before merging.
- **SemVer** and `vX.Y.Z` tags (or `<app>-vX.Y.Z` in a monorepo); the Docker image carries the
  same tag.
- `CHANGELOG.md` updated with every user-visible change.

### 4.5 Tests

- **Pyramid:** lots of unit tests, a fair number of integration tests, and few e2e tests for the
  critical journeys.
- **TDD** for business logic: the failing test comes first.
- **Property-based tests** (Hypothesis / fast-check) wherever there are calculations,
  conversions, or parsers.
- **Integration against real services** in a container; mocks only at the boundary with third
  parties.
- Coverage as a signal, not a target; a reasonable floor in `domain/` and `application/` (≥ 80%).
- Deterministic tests: no dependency on the clock, ordering, or the network. A flaky test gets
  fixed or deleted, never ignored.

### 4.6 CI/CD

Minimal pipeline, in this order; any failure stops the pipeline:

1. **lint + format + types**
2. **tests**: unit → integration → contract
3. **security:** secrets (gitleaks), SAST (Semgrep), dependencies (SCA: `pip-audit`, `npm audit`, Trivy)
4. **build** an **immutable** image, tagged with version and commit, + SBOM
5. **deploy to staging** + migrations + smoke tests (`/health`, critical journeys)
6. **deploy to production with manual approval**, the same image that was tested
7. **post-deploy verification** and a documented, rehearsed **rollback**

### 4.7 Environments and data

- At least three environments: **local, staging, production**. Never real production data
  locally.
- **Versioned, backward-compatible migrations** (expand → migrate → contract) so you can deploy
  and roll back without losing data.
- **Automated backups with periodically tested restores** (an untested backup doesn't count).
- Managed volumes or services for state; nothing persistent inside the image.

### 4.8 Security (OWASP Top 10 / ASVS)

- **Delegated authentication** via an OIDC provider; never hand-roll password management.
- **Server-side authorization, on every endpoint**, least privilege. Hiding a button on the
  front-end is not security.
- **Validate every input** at the boundary (Pydantic, Zod) and parameterized queries or an ORM.
- **Secrets** in a manager or the deployment's environment variables; never in git, images, or
  logs. `.env` only locally.
- **HTTPS always**, security headers (CSP, HSTS, X-Content-Type-Options), restrictive CORS,
  `Secure`/`HttpOnly`/`SameSite` cookies.
- **Limits:** rate limiting, max request and upload size, timeouts on external calls.
- **Uploaded files:** validate real type and size, store outside the served tree, generated
  filename.
- **Containers:** minimal base image, non-root user, no unnecessary exposed ports.
- **Threat model** (STRIDE) in `docs/security/` before opening to users.
- **With LLMs:** treat the model's output as untrusted input, defend against prompt injection,
  never send unnecessary sensitive data, cost and token limits.
- **Personal data (GDPR):** minimization, defined purpose, defined retention, and the ability to
  delete.

### 4.9 Observability

- **Structured (JSON) logs** with level, timestamp, `request_id` / `trace_id`, and no sensitive
  data.
- **`/health` (alive) and `/ready` (ready to serve) endpoints**, no authentication.
- **RED metrics** (rate, errors, duration) per endpoint; traces with **OpenTelemetry**.
- **Alerts** on user-facing symptoms, and **SLOs** for what's critical.

### 4.10 Front-end

- **WCAG 2.1 AA** accessibility: semantics, contrast, keyboard navigation, labels.
- Performance: Core Web Vitals, lazy loading, bundle size watched.
- Responsive design; loading, empty, and error states always covered.
- API client generated from OpenAPI, no hand-duplicated URLs or types.

### 4.11 Documentation

- A `README.md` that lets a newcomer get the project running in < 30 minutes.
- OpenAPI kept current, ADRs for decisions, runbooks for operations, a CHANGELOG for changes.
- Comments explain **why**, not what. Documentation and comments in Spanish.

### Definition of done

1. Tests, lint, and types green, **verified by actually running them** (locally and in CI).
2. If there's a UI, tested in a browser with every affected role.
3. Code review done; `security-review` if it touches authentication, permissions, file uploads,
   personal data, or LLM calls.
4. OpenAPI, CHANGELOG, and documentation updated; an ADR if there was an architecture decision.
5. No secrets or real data in the diff.
6. Deployable: backward-compatible migrations and a possible rollback.

---

## 5. The development pipeline

Every new feature follows these phases, in order. None is skipped. **Typical** skills; each
project's exact table is generated by the kit into its `CLAUDE.md`.

| Phase | What's produced | Skills |
|---|---|---|
| Design | Spec in `docs/superpowers/specs/`; ADR and C4 if the architecture changes | `brainstorming`, `architecture-patterns`, `/c4-architecture` |
| Plan | Plan with small, verifiable tasks | `writing-plans`, `using-git-worktrees`, `/feature-dev` |
| Contract | Updated OpenAPI; DB migration if applicable | `api-design-principles`, `api-documenter` agent, `/sql-migrations` |
| Back-end | Code + tests, on its own branch | `test-driven-development`, `python-type-safety` / `nodejs-backend-patterns`, `fastapi-pro` and `backend-security-coder` agents |
| Front-end | UI + tests + accessibility | `frontend-design`, `wcag-audit-patterns`, `frontend-security-coder` agent, `react-best-practices`, `composition-patterns` |
| Tests | Unit, integration, contract, property-based, e2e | `property-based-testing`, `python-testing-patterns` / `javascript-testing-patterns`, `webapp-testing`, `systematic-debugging` |
| Review | Reviewed merge request | `/code-review`, `/review-pr`, `differential-review`, `find-bugs`, `/git-workflow`, `requesting-code-review` |
| Security | See §6 | `security-review`, `/audit`, `sharp-edges`, `secrets-management` |
| Documentation | README, OpenAPI, CHANGELOG, runbooks | `claude-md-improver`, `api-documenter` agent |
| Deployment | Staging → production with a checklist | `deployment-pipeline-design`, `gitlab-ci-patterns` / `github-actions-templates`, `/config-validate`, `verification-before-completion` |
| Operations | Logs, metrics, traces, SLOs | `slo-implementation`, `distributed-tracing`, `python-observability` |

---

## 6. Security with skills: when to run each one

| Moment | What runs |
|---|---|
| Every change touching authentication, permissions, file uploads, personal data, or LLMs | `security-review` on the diff |
| Before every production deployment | `/audit` (insecure-defaults) + `supply-chain-risk-auditor` |
| Before opening to new users, or once a year | Full audit: `security-audit` supported by `audit-context-building`, `entry-point-analyzer`, `semgrep`, and `variant-analysis`. Report in `docs/security/` |
| When adding a third-party skill | `skill-scanner`, **always**, before installing it |
| Especially sensitive work, when the human asks | Temporarily enable `security-guidance` (never on Claude's own initiative) |

---

## 7. `CLAUDE.md` template

```markdown
# <Project>

<What it is, for whom, what problem it solves. One or two sentences.>

## Stack and architecture
- <Languages, frameworks, DB, authentication, deployment>
- Layered architecture: interfaces → application → domain; infrastructure implements domain interfaces.
- Decisions in docs/adr/; diagrams in docs/architecture/; API in docs/api/openapi.yaml.

## Development pipeline
Design (spec) → plan → contract → back-end → front-end → tests → review → security → docs → deployment.
<The phase → skills table is written by `kit.py table --write CLAUDE.md` between the skills:start / skills:end markers.>

## Rules
- Never work on main: short branch + worktree. Conventional Commits. No push without permission.
- TDD for business logic. Nothing is done without running tests, lint, and types and seeing the result.
- API changes: openapi.yaml first. DB changes: backward-compatible migration.
- Configuration only via environment variables, documented in .env.example.
- Never read, copy, or display the content of .env or any secrets.
- security-review on changes to authentication, permissions, files, personal data, or LLMs.
- Test copies in tmp/. Documentation and comments in <language>.

## Server and security
- Shared server: <hosts> (shared with <shared_with>). | No shared server.
- The shared server is read-only without coordination: checking status and logs is fine;
  changing, stopping, or deleting anything is not.
- No deployments or restarts on it unless the human has already notified <shared_with>
  and confirms it in the conversation.
- `.env` and secrets files are never read or printed (to see the variables, use .env.example).
- Every third-party skill goes through `skill-scanner` first.
- `security-guidance` is never activated on Claude's own initiative: only if the human asks.

## Commands
task setup · task dev · task test · task lint · task typecheck · task build · task migrate · task ci · task skills

## Definition of done
<Copy the one from guide §4.>
```

---

## 8. Starting a project

Use `platform-engineering-playbook/NEW_PLATFORM_PROJECT_PROMPT.md`: in an empty folder, open
Claude Code and type `Read <path>\platform-engineering-playbook\NEW_PLATFORM_PROJECT_PROMPT.md
and follow it to create the project in this folder.` Claude checks that you have the personal
pipeline, interviews you, installs and verifies the skills, designs this guide's structure with
you, and checks that CI, the container, and `/health` work before the first commit.

---

## 9. "Well-built project" checklist

- [ ] `.claude/settings.json` and `.claude/pipeline-skills.json` in the repo; `task skills` is OK (including `security-guidance` disabled and local skills carrying a license)
- [ ] `CLAUDE.md` has the "Server and security" section filled in
- [ ] `README.md` lets the project be started from scratch by following only its steps
- [ ] `CLAUDE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md` present
- [ ] ADR 0001 with the structure decision; an initial `openapi.yaml`
- [ ] `task ci` green locally and the CI pipeline green
- [ ] Commit **and push** hooks installed (§11); a test commit passes them (gitleaks included) and `docs/tech-debt.md` exists
- [ ] In a monorepo: every module has a manifest, a template `CLAUDE.md`, and the boundary checked on every commit (§12)
- [ ] A deployment runbook with a cold backup and rollback; if there's a server, a rehearsal done before the first real deployment (§13)
- [ ] `/health` and `/ready` respond with the app running in Docker
- [ ] `main` protected on GitLab/GitHub (no direct push, review required)
- [ ] No `.env`, secrets, or real data in the history

### Tools every team member should have installed

`git`, `docker` (Docker Desktop on Windows), `uv` (Python), `node` + `npm` (if there's
TypeScript), `go-task`, `pre-commit` (`uv tool install pre-commit`), `gitleaks`.

---

## 10. Plugin map: one primary tool per phase

The kit installs whatever the project's requirements call for. Over time, overlapping plugins
pile up and Claude ends up torn between them, or picks the less suitable one. That's why, once a
project has been running a while, it's worth reviewing the map:

- **One primary tool per phase**, and the rest only if a written condition is met. In
  `CLAUDE.md`, every row of the §5 table carries three columns: "what's produced," "primary," and
  "also, only if..." For example, in Design the primary is `brainstorming`, and
  `c4-architecture` is only used if the architecture changes.
- **Disable at project scope** whatever isn't used or duplicates another, without uninstalling
  it: `claude plugin disable <plugin> --scope project` and `/reload-plugins`. Next to the table,
  note why (e.g. "covers Kubernetes and Terraform, and this deploys with Compose"). Re-enabling
  it needs the watchdog's unlock, because it changes Claude Code's configuration.
- **A skill that doesn't fit** is retired to `tmp/retired_skills/`; it isn't deleted. A
  third-party skill that's actually needed is copied into the project with its `LICENSE` and
  `.upstream-commit`, after being run through `skill-scanner`.
- When to review the map: whenever a new requirement comes in (kit `select`), and whenever you
  see Claude choosing between two similar tools.

---

## 11. Automated gates: before every commit and before every push

Two levels plus a message check, all via `pre-commit` (`.pre-commit-config.yaml`, with
`default_stages: [pre-commit]`, the message one under `stages: [commit-msg]`, and level 2 under
`stages: [pre-push]`). Installed with `default_install_hook_types: [pre-commit, commit-msg,
pre-push]` and `pre-commit install`, inside `task setup`. Watch out: the message hook receives
the file path relative to the repo root; if the script runs from another folder, it has to
resolve it from the root.

| Level | When | What it checks | How long |
|---|---|---|---|
| **1** | Every commit | Format and lint (ruff, oxlint/ESLint), large files, line endings, secrets (gitleaks), and, in a monorepo, the **module boundary** (§12) and that **generated artifacts are current** (catalogs, API clients) | Seconds |
| **Message** | Every commit (`commit-msg`) | A `fix(<module>)` includes, in the same commit, the changelog entry for that module (`CHANGELOG.md` or its own log). Explicit exception in the message: `No-changelog: <reason>` | Instant |
| **2** | Every push | Tests, lint, and types **for the modules that changed** (against `main`, or the push's endpoints), plus the tools' own tests and the contract tests | Minutes |

Rules learned from using this on a real project:
- **Level 2 tests what's on disk, not the commits being sent.** That's why it rejects the push
  if the ref being sent isn't that copy's `HEAD` (`PRE_COMMIT_TO_REF`), or if there are
  uncommitted changes in a folder it's about to test. Otherwise a push could pass with untested
  code.
- **Never `--no-verify`** without the human's explicit permission. An exception to a gate is
  logged in `docs/tech-debt.md` with four fields: **what**, **why it isn't fixed**, **where the
  exclusion lives** (the hook's `exclude:`, a list in a script), and **when it's removed**. An
  exception not in that file doesn't exist: the gate has to pass.
- **Baseline before enabling the hooks:** run everything once and record the result (passing
  tests per module). Whatever was already failing goes into `docs/tech-debt.md` — never hidden.
- **gitleaks false positives:** into `.gitleaksignore`, with the exact fingerprint. The whole
  rule is never disabled.
- A worktree doesn't bring along what git ignores (test data, templates kept out of version
  control, dependencies cloned alongside). If tests need them, the baseline fails falsely: the
  README says what to copy first.

---

## 12. Module structure (monorepo)

When a repo has several applications or tools (§3.2), each one is a **module**: maintained
separately, integrated into the platform through a contract.

- **A manifest per module** (`module.yaml` or equivalent) with what the platform needs to know:
  - `id`, name, and version;
  - which contract version it satisfies;
  - internal port, base path, and health path;
  - data volumes;
  - declared external dependencies;
  - how it shows up in the portal, if there is one.

  Anything shared (the portal's catalog, the proxy's routes, the backup volume list) **is
  generated from the manifests** — never hand-maintained in two places.
- **A versioned contract** (`contract/CONTRACT.md`) with numbered clauses: authentication,
  health, logs (to stdout, no secrets), data, ports. Changing the contract is a platform-level
  change and requires an ADR. Current exceptions live in the contract itself, with their removal
  date.
- **Path-based entry (`domain/<module>`):** the proxy strips the prefix before forwarding the
  request. That's why routes the module **declares** don't carry it, but **every URL sent to the
  browser does**: redirects, where login/logout lands, error-page links, and front-end routes. A
  forgotten `redirect('/')` lands on the portal instead of the module, and it goes unnoticed if
  testing locally by subdomain. Test locally **by path**: the full login-and-back journey, with
  the prefix in place.
- **Boundary checked on every commit:** no module imports code from, or references paths of,
  another module or the platform. This covers Python and TS imports, Dockerfile `COPY`
  instructions, and compose paths; only dependencies declared in the manifest count. Shared
  concerns are designed separately and applied to each module on its own.
- **A `CLAUDE.md` per module** with a fixed template (`docs/templates/CLAUDE_module.md`), with
  these sections:
  - what it is;
  - stack and commands;
  - data and volumes;
  - deviations from the standard (with their ADR);
  - known tech debt.

  The pipeline and security rules aren't repeated: they live in the root `CLAUDE.md`.
- **No-manifest-folder warning:** a test lists versioned `modules/` folders with no manifest.
  This way a half-integrated module never goes unnoticed.
- **A module that doesn't yet comply** (under development, or replacing a legacy one) lives on
  its own branch outside `main` until it has a manifest, a `CLAUDE.md`, a contract, and a catalog
  entry. What's missing goes into an ADR.
- **A legacy module** that can't be adapted internally is integrated with just a wrapper
  (manifest, compose, and health check) and an ADR. Its debt goes into `docs/tech-debt.md`.

---

## 13. Deployment: review, copy, deploy, and know how to roll back

For a Docker Compose deployment on your own server. With Kubernetes or a PaaS, the ideas are the
same, but the orchestrator and its tools handle them.

### 13.1 Before deploying

1. **Local functional review** of every application that changed, in a browser and with every
   role: log in via SSO and walk through the main flows. Tests don't replace this. Anything
   broken is noted as a task before continuing.
2. **Full rehearsal** of the real jump (the version running on the server → the new one), **with
   data**, in an isolated Docker setup (Docker-in-Docker): there, volumes have the same names as
   on the server without colliding with the ones on your laptop. Recognizable data is created in
   each application beforehand (a user, a record, a document) and checked after every step with a
   script.
3. **Coordination:** if the server is shared, notify beforehand and wait for confirmation (the
   `CLAUDE.md`'s "Server and security" section). Nothing runs against the server unless the human
   says so in the conversation.

### 13.2 The deployment tool

A script that's part of the project itself (in `tools/` or `scripts/`) with five commands. The
volume and module lists, and the domain, come from the compose files and the manifests — never a
hand-written list:

| Command | What it does |
|---|---|
| `status` | Deployed version and container status. Read-only. |
| `backup` | A **cold** copy of the data volumes and the `.env` files, with a manifest: git version, date, each file's sha256, `.env` included. |
| `restore` | Restores a backup after validating the manifest and the sha256s. |
| `deploy <version>` | Check → stop → backup → `git merge --ff-only` → bring up with build → health check. |
| `rollback <backup>` | Validate → stop → back up the current state → check out the backup's version → restore → bring up with build → health check. |

Rules, each learned from a real failure:
- **Without `--yes`, it only shows the plan.** Nothing runs without confirmation.
- **Everything that could fail is checked before stopping anything:**
  - clean tree;
  - the target version exists and is a fast-forward;
  - the domain resolves;
  - free disk space;
  - the current version's data volumes exist (ones only the new version brings may be missing);
  - on `rollback`, which modules the target version brings (`git ls-tree`).
- **Cold backup:** the stack is stopped before copying. A hot copy of Postgres or SQLite might
  not restore correctly.
- **The tar is created and verified inside a container**, never with the host machine's `tar`.
  Paths are passed as absolute mounts: a relative path in `-v` creates a volume with an empty
  name.
- **If it fails before touching the code**, the previous stack is simply brought back up. **If it
  fails afterward**, the exact `rollback` command is printed, ready to paste.
- **`rollback` rebuilds the images.** If the two versions share a tag, an `up` without a build
  starts the new code on top of the old data. Better still: tag every image with its version.
- **`rollback` backs up the current state before overwriting it.** If a rollback happens days
  later, that backup is the only record of what was written since.
- **Health is checked three ways:**
  - every service is `running`;
  - every container is `healthy`;
  - every application's `/health` through the proxy, with the `Host` header, since the proxy
    routes by name.

  Watch out: on Docker 29, `docker inspect --format '{{.State.Health.Status}}'` **fails** if the
  container has no healthcheck. Use `{{if .State.Health}}{{.State.Health.Status}}{{end}}`
  instead.
- **Run from a separate worktree**, at the version being deployed, with `--root` pointing at the
  server's tree (required). If it ran from the tree it's deploying, its own checkout would change
  it mid-run.
- **Backups are stored on the server**, in a dedicated folder with restricted permissions.
- **Tests:** unit tests with a fake runner that logs every command, no Docker involved, plus an
  integration test against real Docker on disposable, uniquely-prefixed volumes.

### 13.3 During and after

- Run inside `tmux` or `screen`, and the machine running it must not sleep. In one rehearsal, a
  sleep froze Docker mid-deployment.
- **The builds set the length of the outage.** Building the images before stopping the stack
  cuts the outage down to a few minutes.
- The rehearsal's results (timings, data verified, failures found) go into `docs/reviews/`, and
  the final procedure into the runbook.
