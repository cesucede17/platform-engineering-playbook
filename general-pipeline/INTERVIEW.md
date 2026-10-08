# Personal pipeline interview

**Author:** CSUELA · **Date:** 2026-10-07

This file is the **script** for the interview Claude runs before installing the pipeline. It's
used by `INSTALL_PROMPT.md`; you don't have to read it, though you can if you want to know what
you'll be asked.

- One intro block (block 0) and four blocks of questions (1 through 4).
- **One question at a time**, with options and **one recommended**.
- About 15 questions, taking around 10 minutes.
- Every technical term is explained the first time it comes up, with an analogy and an example.
- **Nothing is installed until you approve the final summary.**
- Each answer fills in one key of `pipeline_profile.json`: the file that stores your answers and
  from which all the configuration is generated (format at the end, in the mapping table).

> **Notes for Claude**
>
> - Ask the questions in this order, one at a time. If you have the `AskUserQuestion` tool, use
>   it (one call per question). It allows at most 4 options; the tool adds the "Other" free-text
>   option on its own, so don't add it yourself. This script's questions all fit that limit.
>   Questions 2.3 and 3.1 are multiple-choice: use them with `multiSelect: true`. Without that
>   tool, write numbered options and wait for the answer.
> - Put the recommended option **first** and add "(recommended)" to its label.
> - Match the depth to the level from question 1.2. Until you know it, explain as if it were
>   "low."
>   - **low:** every new term with an everyday analogy and an example.
>   - **medium:** 1-2 sentences with an example.
>   - **high:** only the unusual or ambiguous bits, in one sentence.
> - If the person doesn't know what to answer, pick the recommended one and tell them: everything
>   can be changed later by redoing the interview.
> - Examples must be generic ("an industrial plant", "the projects folder", "the team's shared
>   server"), unless the human has told you their own.

---

## Block 0. How this is organized (before asking anything)

Claude explains this in its own words, at the human's level; it doesn't need to be read verbatim.
If the level isn't known yet, explain it simply.

### 0.1 The 3 guides and their order

- **`general-pipeline`** (this one) is installed **once** per person, into your Claude Code
  configuration folder (`~/.claude`). It applies to all your projects.
  - `~` is your home folder: on Windows, `C:\Users\<your user>`; on Linux, `/home/<your user>`.
  - `~/.claude` is where Claude Code stores your configuration — like the desk drawer where you
    keep your personal tools, the ones you use on any job.
- **`ml-engineering-playbook`** or **`platform-engineering-playbook`** are used **when creating
  each project**: one for machine learning projects (e.g. a model that predicts an industrial
  plant's energy use) and the other for platforms and web applications. They need the general
  pipeline installed first.

### 0.2 The pieces

| Piece | What it does, in one sentence | Example |
|---|---|---|
| **guardian** | The watchdog that stops you from deleting or breaking important things. It's a *hook*: a small program Claude Code runs automatically before every action, like a gate guard checking every package before it leaves. | If Claude tries to delete a whole project folder outright, guardian stops it. |
| **continuity** | When you open Claude Code, it tells you where you left off. | You open Claude in your project and see: "Last session: yesterday; next step: review the data cleaning." |
| **journal & tasks** | The journal is a summary of each day's work (like a site diary); tasks are your dated to-do list. | You say "done for today" and Claude writes the summary; you say "remind me to review the report on Friday" and it's added to the list. |
| **`/explain`** | A command that explains any technical term with an example. | `/explain cross-validation`. |
| **`/improve-pipeline`** | A *skill* for extending all of this later, in an orderly way, without breaking anything. A skill is a recipe Claude follows step by step when it needs it. | You see a new tool you're interested in, and Claude helps you review it, compare it with what you have, and adopt it. |

The **superpowers** plugin is also installed (a *plugin* is a package of skills added to Claude
Code, like a browser extension). It's required: the improvement process depends on it.

### 0.3 What the interview is like

- 4 blocks: your profile, your protections, how you like to work, and your environment (Claude
  figures out almost all of this last one by itself).
- About 15 questions, around 10 minutes.
- There's always a recommended option. If unsure, pick it.
- Everything can be changed later by redoing the interview.
- Nothing is installed without your approval of the summary.

### 0.4 Where the configuration lives

- Your answers are saved in `~/.claude/pipeline_profile.json`.
- Before installing, a **backup** of `~/.claude` is made at `~/.claude/pipeline_copies/<date>/`.
  If something doesn't sit right, you can roll back with `install.py undo`.

### 0.5 Wrap-up

End with: **"Shall we start?"**

---

## Block 1. Profile and level

### 1.1 What do you mainly work on?

| Option | Profile value |
|---|---|
| Machine learning and data | `"ml"` |
| Platforms and web applications | `"platforms"` |
| Both | `"both"` |

- **Recommended:** none is objectively better; if unsure, `"both"`.
- **Key:** `focus`.
- **What it's for:** decides which project guide is recommended at the end
  (`ml-engineering-playbook`, `platform-engineering-playbook`, or both), and steers which examples
  Claude uses during this conversation. It doesn't change anything about the installed
  configuration.

### 1.2 How much experience do you have with git, the terminal, and Claude Code?

| Option | Profile value | How Claude will explain things from now on |
|---|---|---|
| Little | `"low"` | Every new term with an everyday analogy and an example. |
| Some | `"medium"` | Uncommon terms, in 1-2 sentences with an example. |
| A lot | `"high"` | Only rare or ambiguous terms, in one sentence. |

- **Recommended:** whichever is true. If torn between two, pick the lower one: better to
  over-explain than to leave a gap.
- **Key:** `level`.
- **Explanation for the human (at "low"):** *git* is a system that keeps versions of your files,
  like a shared document's change history; the *terminal* is the window where you type commands
  instead of clicking buttons.

### 1.3 What language do you want Claude to reply in?

| Option | Profile value |
|---|---|
| Spanish | `"spanish"` |
| English | `"english"` |
| Other (write which) | the written language, lowercase |

- **Recommended:** Spanish.
- **Key:** `language`.
- **What it's for:** goes into the "Always reply in …" line of the block added to your
  `~/.claude/CLAUDE.md`. `CLAUDE.md` is an instructions file Claude reads at the start of every
  conversation — like the note you leave for whoever covers for you on vacation.

---

## Block 2. Protections (guardian)

Before this block, Claude briefly explains what guardian is if it hasn't already (block 0), and
flags something important: **guardian starts in trial mode for 7 days**.

- In **trial mode** it blocks nothing, except attempts to touch its own configuration or create
  the unlock file: it only logs, for the record, what it *would have* blocked.
- After 7 days you'll have a task in your list: review that log with Claude and switch to
  **active mode**, where it actually blocks. It's like setting a new alarm to warning-only mode
  for a few days, to make sure it doesn't trip over the cat before wiring it to the control
  panel.

### 2.1 What's your projects root folder?

The *root folder* is the one containing every project's folder, one per project (e.g.
`C:/Users/<your user>/projects`, with `consumption_forecast/`, `annual_report/`... inside it).

- **Options:**
  - the folder Claude proposes: the one Claude Code was opened from, if it contains projects
    (before proposing it, Claude runs `install.py detect --root` on it and looks at which git
    projects it finds);
  - another one (the human types it);
  - if you work across more than one root, several can be given.
- **Recommended:** the detected one, if correct.
- **Key:** `roots` (list of absolute paths written with `/`).
- **What it's for:** guardian watches what's inside more carefully (e.g. deleting an entire
  project), and continuity uses this folder for the all-projects overview.

### 2.2 Which folders should never be touched?

Claude proposes what it detected, and the human adds or removes from the list.

- **Options (the proposed ones):**
  - `OBSOLETE` folders (old material kept for reference);
  - any `data/raw` in any project (the original data, exactly as it arrived);
  - external repositories you use but don't own (e.g. another team's code that you only ever
    call from your project).
- **Recommended:** all detected ones, plus `data/raw` always.
- **Keys:**
  - `protected_paths`: the specific folders, with their absolute path (e.g.
    `C:/Users/<your user>/projects/OBSOLETE`);
  - `protected_segments`: path fragments that are protected **wherever they appear**, like
    `data/raw` (protects `project_a/data/raw`, `project_b/data/raw`...);
  - `read_only`: the external repositories. They **also** go into `protected_paths`. In
    addition, continuity treats them as part of the root: the journal is never written inside
    them.
- **Explanation for the human:** original data is like the signed minutes of a meeting: you can
  make copies and work on those, but the original is never touched. If a protected folder ever
  genuinely needs touching, it can be manually unlocked for 2 hours (explained in block 2.3).
- **Note for Claude:** if there are more than 3 proposals, they don't fit as `AskUserQuestion`
  options. Show them as a list and ask "Protect all of them?" with the options "Yes, all
  (recommended)" and "I want to change some."

### 2.3 Which safeguards do you want active?

A **multiple-choice** question: the human checks the ones they want. Anything left unchecked is
disabled.

| Option | What it stops | Rule (for the profile) |
|---|---|---|
| Mass deletions | Deleting a whole folder, or everything in a project, at once. | `mass-deletion` |
| Destructive git | git commands that lose work with no way back, like rewriting shared history or discarding all unsaved changes. | `destructive-git` |
| Docker data loss | Commands that delete Docker *volumes* (the disks where containers keep their data, like a database). | `docker-data` |
| Quality gates | Changing the config of the tools that review code (e.g. the style checker or the test runner), so no one relaxes them without noticing. | `quality-gates` |

- **Recommended:** **all checked** (the default).
- **Key:** `disabled`, with the rules that are **not** checked. If all are checked,
  `"disabled": []`.
- The `server` rule isn't asked about here: it depends on question 2.4 and is always active. If
  no server is configured, it doesn't affect anything.

**What can't be disabled, and why.** Claude explains it like this, in its own words:

> Three protections are always on and don't appear in the list:
>
> - **Claude Code's own configuration** (`self-protection`): stops Claude from changing its own
>   settings or the watchdog's code;
> - **the protected folders** from the previous question (`protected-path`);
> - **the unlock mechanism** (`unlock`): Claude can't create the file that frees up a folder —
>   only you can create it, by hand.
>
> The reason is simple: **if these could be turned off, Claude could turn off the watchdog
> itself.** It would be like a security guard holding the key to his own alarm's switch.

**How to unlock something, when it's genuinely needed** (explained here, once):

- If guardian blocks an action, Claude tells you, explains why it's needed, and points you to a
  folder.
- You manually create an empty unlock file in that folder (guardian's message says its exact
  name).
- That folder stays unlocked for **2 hours**; after that it stops working on its own.
- Claude never tries to work around a block (not even with a script).

### 2.4 Do you work with any shared server?

A shared server is a team machine you connect to from your own, running applications other
people use (e.g. the team's shared server where a web application is deployed).

- **Options:**
  - "No" (recommended if unsure);
  - "Yes": Claude then asks, one thing at a time:
    1. its name or IP address (there can be several: short name, full name, and IP);
    2. who it's shared with (e.g. "the systems team").
  - If there's more than one server, both questions repeat for each.
- **Recommended:** "No," unless there is one.
- **Key:** `servers`, a list with one entry per server:
  `{"hosts": ["<name>", "<IP>"], "shared_with": "<with whom>"}`. If none, `[]`.
- **What it's for:**
  - guardian allows only *looking* on the server (checking status, reading logs) and blocks any
    change;
  - `CLAUDE.md` gets a reminder to notify whoever shares it, beforehand.

---

## Block 3. How you like to work

### 3.1 What do you want to see when you open Claude Code?

A **multiple-choice** question.

| Option | What it shows | Sections (for the profile) |
|---|---|---|
| Where you left off | The date of that project's last session and its "next step." | `session` |
| Pending and overdue | That project's tasks, any past their date, and a flag if other folders have pending tasks. | `tasks`, `other` |
| git status | One line with the branch and whether there are unsaved git changes. | `git` |
| All-projects overview | If Claude opens at the root folder: one row per project with its last session and tasks. | `overview` |

- **Recommended:** **all checked**.
- **Key:** `startup_sections`, the list of checked sections, in this order:
  `["session", "tasks", "git", "other", "overview"]`.

### 3.2 Do you want a summary at the end of the day?

When you say "done for today" (or "wrapping up," "that's it for today," "end of day"):

| Option | What happens | Profile value |
|---|---|---|
| Automatic | Claude writes the summary without asking, shows it to you, and proposes pending items as tasks. | `"automatic"` |
| Ask first | Claude asks whether you want it, before writing. | `"ask"` |
| No | It's only written on request. | `"no"` |

- **Recommended:** automatic. The summary is what lets the next day's startup tell you where you
  left off.
- **Key:** `journal_closing`.

### 3.3 Where is the journal kept?

| Option | Where | Profile value |
|---|---|---|
| In each project | In `docs/journal/` inside each project: the summary travels with the project. | `""` (empty) |
| In one central folder | All together in a folder you choose, with one subfolder per project. Claude then asks which folder. | that folder's absolute path, with `/` |

- **Recommended:** in each project.
- **Key:** `central_journal`.

### 3.4 Which folders in your root are projects?

Claude shows the folders inside the root:

- the ones with git are marked as projects;
- the rest are shown separately, asking which ones are **not** projects (e.g. a folder of loose
  documents or backups).

Every project has a **label**, which is its folder name: that project's tasks are tagged with it
(e.g. `[consumption_forecast] Review March's data]`). Tasks that don't belong to any project get
the `[general]` label.

- **Options:** "Yes, that's right (recommended)" · "I want to change some."
- **Recommended:** the detected ones.
- **Key:** `excluded`. Folders that are **not** projects are added by name to the base list
  `["OBSOLETE", "tmp", "docs"]`, so they don't show up in the overview. Folders that *are*
  projects aren't stored: they're detected fresh every time Claude Code opens.

### 3.5 How do you want Claude to handle large tasks?

| Option | What happens | Profile value |
|---|---|---|
| In phases, with subagents and reviews | Claude splits the work into phases, hands each one to a *subagent* (another Claude instance working separately, like an assistant given one specific job) and reviews each phase before continuing. | `"subagents"` |
| Step by step, asking | Claude does one step, shows it to you, and asks before the next. | `"step_by_step"` |

- **Recommended:** phases with subagents if the level is "medium" or "high"; step by step if
  "low" (so you can see and understand every step).
- **Key:** `execution`.

---

## Block 4. Environment (Claude detects this; it only asks what it can't figure out)

Claude runs `install.py detect` and reports the result in two or three sentences. It only asks if
something's missing.

### 4.1 OS, Python, git, and Docker

- **Detected:**
  - the OS (Windows or Linux);
  - the *Python launcher*: the name used to start Python on your machine (`python3`, `python`,
    or `py`), version 3.10 or later;
  - whether git and Docker are present.
- **Keys:** `system` and `python`.
- **If there's no Python 3.10 or later:** Claude stops and explains how to install it; the
  install can't continue without it.
- **If git or Docker is missing:** it just warns; the pipeline installs anyway (git will be
  needed for projects; Docker only if you use it).

### 4.2 Do you already have configuration in `~/.claude`?

- **Detected:** what's already in `~/.claude` (hooks, `CLAUDE.md`, skills...).
- **No question asked here:** it just reports. Nothing is ever overwritten without warning:
  - a backup is made first;
  - in `settings.json`, the two hooks are **added** and everything else is kept;
  - in `CLAUDE.md`, the pipeline block goes between the `<!-- pipeline:start -->` and
    `<!-- pipeline:end -->` markers; whatever was already there stays untouched;
  - if a guardian or continuity config already exists, it's kept by default. Claude will see this
    while preparing the install (the installer says "kept") and will then ask whether to keep it
    or replace it with the one from your answers (the `--reconfigure` option; guardian's mode,
    trial or active, is preserved either way);
  - if guardian **was already installed**, the installer writes nothing until you first manually
    create the unlock file in `~/.claude/` (valid for 2 hours). It's the watchdog protecting
    itself: Claude will ask for this when the time comes.

### 4.3 Do you already have a `TASKS.md`?

- **Detected:** whether `~/.claude/TASKS.md` (your task list) exists.
- **No question asked:** if it exists, it's reused and only the guardian-review task is added; if
  not, it's created.

---

## Summary and approval

At the end, Claude shows a summary of every answer, in plain language (not the JSON), e.g.:

> - You work mainly on: machine learning and data. Level: low. Language: Spanish.
> - Projects folder: `C:/Users/<your user>/projects`.
> - Protected folders: `…/projects/OBSOLETE` and any `data/raw`.
> - Safeguards: all active. Shared server: no.
> - On opening Claude you'll see: where you left off, pending items, git, and the overview.
> - End-of-day summary: automatic, per project.
> - Large tasks: step by step.
> - guardian starts in trial mode; on (date + 7 days) you'll have the task to switch it to active.

And asks: "Does this look right?" Options: "Yes, go ahead (recommended)" · "I want to change
something." If they want to change something, only that question is repeated and the summary is
shown again.

---

## Mapping table: question → profile key

Format `pipeline_profile.json`, version 1. **Every** key is listed.

| Key | Comes from | Values |
|---|---|---|
| `format` | Fixed | `1` |
| `short_name` | **Automatic:** your home folder's name (the last segment of `~`), lowercased. Only identifies the profile. | e.g. `"jane"` |
| `focus` | Question 1.1 | `"ml"`, `"platforms"`, or `"both"` |
| `level` | Question 1.2 | `"low"`, `"medium"`, or `"high"` |
| `language` | Question 1.3 | e.g. `"spanish"` |
| `system` | **Automatic:** `install.py detect` (question 4.1) | `"windows"` or `"linux"` |
| `python` | **Automatic:** `install.py detect` (question 4.1). The launcher hooks are run with. | `"python"`, `"python3"`, or `"py"` |
| `home` | **Automatic:** the `home` key from `install.py detect` (your home folder, full path, written with `/`) | e.g. `"C:/Users/jane"` or `"/home/jane"` |
| `roots` | Question 2.1 | list of absolute paths with `/` |
| `protected_paths` | Question 2.2 (plus external repos) | list of absolute paths with `/` |
| `protected_segments` | Question 2.2 | e.g. `["data/raw"]` |
| `disabled` | Question 2.3 (the unchecked ones) | subset of `mass-deletion`, `destructive-git`, `docker-data`, `quality-gates`, `server`; nothing else |
| `servers` | Question 2.4 | list of `{"hosts": [...], "shared_with": "..."}`, or `[]` |
| `startup_sections` | Question 3.1 | subset of `["session", "tasks", "git", "other", "overview"]` |
| `journal_closing` | Question 3.2 | `"automatic"`, `"ask"`, or `"no"` |
| `central_journal` | Question 3.3 | `""` (per project) or an absolute path with `/` |
| `read_only` | Question 2.2 (the external repos) | list of absolute paths with `/`, or `[]` |
| `excluded` | **Automatic, with confirmation** (question 3.4): the base list `["OBSOLETE", "tmp", "docs"]` plus the names of root folders that aren't projects | list of folder names |
| `execution` | Question 3.5 | `"subagents"` or `"step_by_step"` |
| `guardian_initial_mode` | **Fixed:** guardian always starts in trial mode (reinstalling or reconfiguring keeps whatever mode it already has) | `"trial"` |
| `install_date` | **Automatic:** today's date, as `YYYY-MM-DD`. The guardian-review task is set for 7 days later. | e.g. `"2026-10-06"` |

Full example (an ML person, on Windows, no server):

```json
{
  "format": 1,
  "short_name": "jane",
  "focus": "ml",
  "level": "low",
  "language": "spanish",
  "system": "windows",
  "python": "python",
  "home": "C:/Users/jane",
  "roots": ["C:/Users/jane/projects"],
  "protected_paths": ["C:/Users/jane/projects/OBSOLETE"],
  "protected_segments": ["data/raw"],
  "disabled": [],
  "servers": [],
  "startup_sections": ["session", "tasks", "git", "other", "overview"],
  "journal_closing": "automatic",
  "central_journal": "",
  "read_only": [],
  "excluded": ["OBSOLETE", "tmp", "docs"],
  "execution": "step_by_step",
  "guardian_initial_mode": "trial",
  "install_date": "2026-10-06"
}
```

File rules:

- Saved as UTF-8.
- All paths are absolute and use `/`, Windows included.
- If `disabled` contains anything other than the five disable-able rules (e.g.
  `self-protection`), the installer rejects it.

---

## Redoing the interview later

To change something (e.g. adding a protected folder or a server), type the same install sentence
again: `Read <PATH>/general-pipeline/INSTALL_PROMPT.md and follow it`. Claude sees that
`~/.claude/pipeline_profile.json` already exists and then:

1. Reads the profile and shows a plain-language summary of the current answers.
2. Asks **what you want to change**: a whole block, individual questions, or nothing (just update
   the pieces to the guide's latest version).
3. Asks only those questions, with the current answer shown as the option marked "(current)."
4. Copies the profile to a temp folder, changes those keys, and sets `install_date` to today. The
   automatic keys are re-detected (in case you switched machines or Python versions).
5. Shows the summary with changes marked, and asks for approval, as the first time.
6. Installs. Uses `--reconfigure` **only if an answer from blocks 2 or 3 changed**: those answers
   live in guardian's and continuity's configuration, which is otherwise kept as-is.
   - If only block-1 answers changed, or you just want to update the pieces, it's not needed:
     the `CLAUDE.md` block is always regenerated.
   - `--reconfigure` keeps whatever guardian mode you have (if you already switched it to active,
     it stays active) and, in that case, doesn't re-add the review task.
7. Since guardian is already installed, the installer writes nothing (it exits with code 4)
   until you manually create the unlock file in `~/.claude/`. Claude asks for this and, once you
   confirm it's done, repeats the install. The unlock expires on its own after 2 hours.
