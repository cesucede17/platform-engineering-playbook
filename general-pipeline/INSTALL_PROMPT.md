# Prompt: install the personal pipeline (general guide)

**Author:** CSUELA · **Date:** 2026-10-07

> **How to use this (human):** open Claude Code (in your projects folder, if you have one) and
> type:
>
> ```text
> Read <PATH>/general-pipeline/INSTALL_PROMPT.md and follow it
> ```
>
> (`<PATH>` is the folder where you have the guides). Claude will explain how everything is
> organized, ask you about 15 questions, show you a summary, and — only once you approve — install
> and verify each piece. You just answer and approve. Takes about 15 minutes.
>
> Everything below is addressed to Claude.

---

## Instructions for Claude

You're going to install this person's personal Claude Code pipeline into their `~/.claude`
folder. `GUIDE` is the folder containing this file (`general-pipeline`). In it you'll find:

- `INTERVIEW.md`: the interview script (block 0 and blocks 1 through 4) and the profile format;
- `tools/install.py`: the installer;
- `components/` and `templates/`: what gets installed (don't touch these).

Follow the phases **in order**. Each phase has a **gate**: don't move to the next one until it's
met.

### Rules for the whole process

- **Language and tone.** Reply in Spanish (or whichever language they pick in question 1.3, from
  that point on). Speak plainly. Explain each technical term the first time it comes up, at the
  level from question 1.2:
  - **low:** an everyday analogy and an example; short sentences; one step at a time;
  - **medium:** 1-2 sentences with an example;
  - **high:** only the unusual bits, in one sentence.
  Until you know the level, explain as if it were "low." Use generic examples ("an industrial
  plant", "the projects folder", "the team's shared server") unless the human gives you their
  own.
- **One question at a time.** If you have the `AskUserQuestion` tool, use it for every question
  (one call per question, at most 4 options, the recommended one first and labeled
  "(recommended)"). The tool adds the "Other" free-text option on its own — don't add it
  yourself. Questions 2.3 and 3.1 are multiple-choice: use `multiSelect: true`. Without that
  tool, write numbered options and wait for the answer.
- **Nothing is installed without approval.** Don't run `install.py install --yes` until the
  human has explicitly approved, in this conversation, the summary (phase 3) and the
  `settings.json` change (phase 6).
- **Only the installer writes to `~/.claude`.** You never hand-create or hand-edit anything
  inside `~/.claude` (not `settings.json`, not the hooks, not `CLAUDE.md`, not `TASKS.md`):
  `install.py` does it, after first making a backup. You only write the profile, and in a
  temporary folder (phase 4) — never inside the human's own projects.
- **guardian is never bypassed.** If guardian was already installed (you'll see this in phase 1),
  it can stop you two ways: blocking one of your actions (a guardian message appears), or because
  `install.py install --yes` or `undo --yes` exits with **code 4** (see below). In both cases:
  1. stop and show the message;
  2. explain in one or two plain sentences why that step is needed. For example, at "low":
     "The watchdog protects its own configuration, like a safe that only its owner can open. To
     install, it needs you to grant permission for a little while.";
  3. ask the human to **manually** create the unlock file in the folder the message names (with
     code 4, inside `~/.claude/`), via File Explorer or a terminal; the message says its exact
     name. It unlocks that folder for **2 hours** and expires on its own after that;
  4. once they confirm it's done, repeat the exact same command.
  Don't try to work around it — not with a script, not with an equivalent command, not by moving
  or renaming files. You never create that file yourself, nor write its name into a command.
- **Nothing is accepted without seeing the output.** Show what matters from every command. If a
  command fails, explain the error plainly and don't improvise fixes inside `~/.claude`: the safe
  way out is `install.py undo` (phase 8).
- **`install.py` exit codes:** 0 ok; 1 error; 2 some check failed; 3 "approval needed" (the normal
  result of running `install` or `undo` without `--yes`: it shows what it would do and changes
  nothing); 4 "guardian is already installed and the unlock is missing": it wrote nothing, and
  the rule above resolves it. Doesn't appear on a first install. Without `--yes`, if the unlock
  will be needed, the installer already warns about it (and exits with 3).

### How commands are written

- `PY` is the Python launcher you find in phase 1 (`python3`, `python`, or `py`). Usually
  `python3` on Linux.
- Write paths with `/` and in quotes, Windows included:
  `PY "GUIDE/tools/install.py" detect`.
- Options go after the command: `--profile P` (profile path), `--root R` (a projects folder;
  repeat if there are several), `--yes` (approval given), `--reconfigure` (replaces any existing
  guardian/continuity config with the one from the profile; guardian's mode, trial or active, is
  kept), `--no-plugins` (skips installing/checking the superpowers plugin). Don't use `--home`:
  that's for testing only.

---

### Phase 1 — Check the machine

1. **Python launcher.** Try, in this order, `python3 --version`, `python --version`, and
   `py --version`, and keep the first one that gives Python 3.10 or later: that's `PY`.
   - If none work, stop. Explain that Python 3.10+ is required, how to install it (on Windows,
     from python.org, checking "Add python.exe to PATH"; on Linux, via the distro's package
     manager), and that they should retype the install sentence once done.
2. **What's on the machine.** Run `PY "GUIDE/tools/install.py" detect`. It returns JSON with:
   - `system`, `python`, and `home` (the home folder, full path, with `/`): these go straight
     into the profile; `home`'s last segment, lowercased, becomes `short_name`;
   - `git` and `docker`: if either is missing, warn (git will be needed for projects; Docker only
     if they use it), but continue;
   - `existing_claude`: what's already in `~/.claude`;
   - `existing_tasks`: whether a task list already exists.
3. **Automatic profile data.** Get:
   - the system's temp folder:
     `PY -c "import tempfile; from pathlib import Path; print(Path(tempfile.gettempdir()).resolve().as_posix())"`;
   - today's date as `YYYY-MM-DD` (goes into `install_date`).
4. **First time or repeat?** Check whether `~/.claude/pipeline_profile.json` exists (read it with
   the file-reading tool, not a shell command).
   - If it does **not** exist: it's a fresh install. Continue to phase 2.
   - If it **does** exist: it's a repeat run. Continue to phase 2 in **repeat mode** (below).
5. **Is guardian already installed?** If `existing_claude` includes `hooks` and
   `~/.claude/hooks/guardian.py` already exists, guardian is active in this session. Keep that in
   mind for the unlock rule above.

**Gate:** you have `PY`, the `detect` JSON, `home`, the temp folder, and the date, and you know
whether this is a fresh install or a repeat.

---

### Phase 2 — Context brief and interview

Read the whole of `GUIDE/INTERVIEW.md` before starting.

**Fresh install:**

1. Give the **context brief** in your own words, at the "low" level (you don't know their level
   yet), and end with "Shall we start?" Wait for the answer.
2. Run through blocks 1, 2, and 3 **one question at a time**, with their options and recommended
   choice, exactly as `INTERVIEW.md` describes. From question 1.2 onward, match the tone to the
   chosen level.
3. **Question 2.1 (projects root).** Before proposing anything, run
   `PY "GUIDE/tools/install.py" detect --root "<folder>"` with the folder Claude Code was opened
   from, and look at `project_candidates`:
   - if that folder isn't the home folder and it contains projects, propose it as the root,
     naming what it found;
   - otherwise, ask directly where they keep their projects and re-run `detect --root` with that
     folder before confirming it.
   If they have several roots, pass one `--root` per folder. Once the root is confirmed, the JSON
   also includes:
   - `protected_candidates`: `OBSOLETE` and `data/raw` folders found; use these in 2.2. The
     `OBSOLETE` ones go into `protected_paths` with their path; the `data/raw` ones aren't listed
     individually — the `"data/raw"` entry in `protected_segments` covers them;
   - `project_candidates`: the root's git subfolders; use these in 3.4 (list the root's other
     subfolders yourself to ask which ones aren't projects).
4. **Question 2.2.** Also ask whether they use any external repository that should never be
   modified (e.g. another team's code that's only ever called from a project). Those go into
   `protected_paths` and `read_only`.
5. **Question 2.3.** Explain, with the sentence from `INTERVIEW.md`, what can't be disabled and
   why: "if these could be turned off, Claude could turn off the watchdog itself."
6. **Block 4.** Don't ask what you already know from `detect`: state it in two or three sentences
   (which OS and Python, whether git and Docker are present, whether `~/.claude` already had
   config and that nothing will be overwritten, whether `TASKS.md` already existed and that it
   will be reused).

**Repeat mode** (`~/.claude/pipeline_profile.json` already exists):

1. Explain in one sentence that the pipeline is already installed and that you'll start from
   their previous answers.
2. Show a plain-language summary of their current profile (like the one in phase 3). Use their
   `level` for tone from the start.
3. Ask what they want to do:
   - "Just update the pieces to this guide's version (recommended if you don't want to change
     answers)";
   - "Change some answers";
   - "Redo the whole interview."
4. If they want to change answers, ask which blocks or questions, and go through them one at a
   time with the current answer marked "(current)." Don't re-run the context brief unless asked.
5. Always re-detect the automatic keys (`system`, `python`, `home`) and set `install_date` to
   today.
6. Since guardian is already installed, `install --yes` will ask for the unlock (code 4). Mention
   this now, in one sentence, so it doesn't come as a surprise.

**Gate:** you have an answer for every question (or the current one, in repeat mode).

---

### Phase 3 — Summary and approval

1. Show the summary in plain language, as in the "Summary and approval" section of
   `INTERVIEW.md` (not the JSON). In repeat mode, mark what's changing from before.
2. Ask "Does this look right?" with the options "Yes, go ahead (recommended)" and "I want to
   change something."
3. If they want to change something, repeat just that question and show the summary again.

**Gate:** the human has explicitly said yes.

---

### Phase 4 — Write the profile to a temporary folder

1. Create the `pipeline_profile.json` profile in `<system temp folder>/pipeline_profile/` using
   the file-writing tool (not `echo`, not redirection):
   - with **all** the keys from format 1 (the mapping table in `INTERVIEW.md`);
   - in UTF-8, with absolute paths written using `/`;
   - `guardian_initial_mode` always `"trial"`;
   - `disabled` only with rules from the disable-able list (`mass-deletion`,
     `destructive-git`, `docker-data`, `quality-gates`, `server`).
   That file is `P`. Never save it inside the human's own projects or inside `GUIDE` (which may
   be a shared folder). The installer will copy its contents into
   `~/.claude/pipeline_profile.json`.
2. In repeat mode, start from their existing profile: copy its contents into the temp file and
   change only the keys that changed, plus the automatic ones.

**Gate:** `P` exists and has every key (read it back and check).

---

### Phase 5 — Prepare and show the changes

1. Run `PY "GUIDE/tools/install.py" generate --profile "P"` (add `--reconfigure` in repeat mode
   if any answer from blocks 2 or 3 changed).
   - This fills in the configuration under `~/.claude/pipeline_copies/staging/` (nothing installed
     yet) and reports, file by file, whether it's new, unchanged, how many lines differ, or
     `keeping the installed one (use --reconfigure to change it)`.
   - If it exits with 1, explain the error (almost always a malformed profile key), fix `P`, and
     retry.
   - **If, on a fresh install, "keeping" shows up** for the guardian or continuity config, there
     was already one from before (e.g. a manual install). The version generated from their
     answers stays in `staging/` just for comparison. Explain this and ask: "Keep what you have
     (recommended if you configured it by hand)" or "Replace it with what your answers produce."
     If they choose to replace it, use `--reconfigure` here and in the following steps; guardian's
     mode is preserved either way.
2. Show the human the block that will be added to their `CLAUDE.md`: read it from
   `~/.claude/pipeline_copies/staging/CLAUDE.md` (only the part between
   `<!-- pipeline:start -->` and `<!-- pipeline:end -->`). Explain that this is what Claude reads
   at the start of every conversation, and that whatever was already in that file stays
   untouched.
3. Run `PY "GUIDE/tools/install.py" install --profile "P"` **without** `--yes` (plus
   `--reconfigure` if used in step 1). It will exit with code 3: that's expected. Show:
   - the file list (`new`, `changed`, `kept`, `removed`);
   - the **full `settings.json` diff**.

**Gate:** the human has seen the change list and the `settings.json` diff.

---

### Phase 6 — Approve `settings.json` and install

1. Explain the `settings.json` change, at their level. For example, at "low":

   > `settings.json` is Claude Code's settings file, like your phone's settings panel. Two
   > "do this automatically" lines get added:
   >
   > - **before every action** of Claude's that edits files or runs commands, route it through
   >   guardian (the watchdog);
   > - **when Claude Code opens**, run continuity (the summary of where you left off).
   >
   > Everything else already in that file stays as it is. Before touching anything, your
   > `~/.claude` gets backed up.

   Also mention that the **superpowers** plugin (required) will be installed. If the previous
   step warned that the unlock will be needed, remind them now: after saying yes, the installer
   may exit with code 4, and you'll then ask them to create the file.
2. Ask for explicit approval: "Do you approve the `settings.json` change and the install?", with
   the options "Yes, install" and "No, not yet." If they say no, stop: nothing has changed (at
   most, the unused `staging/` folder).
3. On a yes, run `PY "GUIDE/tools/install.py" install --profile "P" --yes` (plus `--reconfigure`
   if applicable). Give it a long timeout (around 10 minutes): installing the plugin downloads
   files.
   - Show where the backup landed ("Backup created at …").
   - If a `WARNING` about the plugin shows up (e.g. the `claude` program isn't found, or there's
     no network), note it for the report: phase 7 will check it.
   - If it exits with 4, nothing was written: follow the guardian rule above (the human manually
     creates the unlock file in `~/.claude/`) and, once confirmed, repeat the same command.
   - If it exits with 1, show the error, explain plainly what happened, and offer to roll back
     with `undo` (phase 8). Don't try to fix it by hand.

**Gate:** `install --yes` exited with 0.

---

### Phase 7 — Verify

1. Run `PY "GUIDE/tools/install.py" verify --profile "P"`. It genuinely checks:
   - **guardian:** sends it a test command and confirms it's logged;
   - **continuity:** runs the startup flow and confirms it displays;
   - **skills and commands:** that they're in place;
   - **hooks:** that `settings.json` has both;
   - **superpowers:** that the plugin is installed and enabled.
2. If it exits with 2, some check is `FAILED`. Explain which and what it means:
   - **superpowers** is the most common failure (no network, or the `claude` program isn't on the
     PATH — the list of folders the system searches for programs). Ask the human to install it
     themselves in a terminal (or in Claude Code, typing `!` first):
     `claude plugin marketplace add anthropics/superpowers-marketplace` then
     `claude plugin install superpowers@superpowers-marketplace --scope user`. Then re-run
     `verify`.
   - For any other failure, show the text, explain the likely cause, and offer `undo`. Don't
     hand-edit files inside `~/.claude`.

**Gate:** you have the result of every check (OK or FAILED).

---

### Phase 8 — Final report

Write a short report, at the human's level, with:

1. **Checks:** one line per `verify` check, with **OK** or **FAILED**.
2. **What was installed:** guardian (in trial mode on a fresh install; in a repeat, whatever mode
   it already had), continuity, journal and tasks, `/explain`, `/improve-pipeline`, and
   superpowers; and where the backup landed.
3. **guardian's pending task:** their `TASKS.md` now has a dated task (install date + 7 days) to
   review guardian's log with Claude and switch it to active mode. That change is made by the
   human, by hand, editing `"mode": "trial"` to `"mode": "active"` in
   `~/.claude/hooks/guardian_rules.json`: Claude can't touch that file. If `TASKS.md` already had
   that task, don't duplicate it (if guardian was already active, it can be marked done).
4. **The manual step:** "**Close and reopen Claude Code; you should see the startup summary.**"
   Explain what they'll see: a block starting with `=== <folder name> — overview ===` (if Claude
   opens at the root folder) or `=== <project name> — resuming ===` (if opened inside a project).
   On the first day it'll be mostly empty: there are no sessions or tasks for that project yet.
5. **Next step:** per question 1.1, for each new project, `ml-engineering-playbook` (ML and
   data), `platform-engineering-playbook` (platforms and web), or both.
6. **How to roll back (`undo`):**
   - `PY "GUIDE/tools/install.py" undo` shows what would be restored and **which files the human
     has changed since installing** (those changes would be lost). Changes nothing.
   - `PY "GUIDE/tools/install.py" undo --yes` restores `~/.claude` to how it was before the last
     install. It first saves a copy of the current state (the "pre-undo" backup), so nothing is
     lost. Running it again undoes the install before that one.
   - Since guardian is installed, `undo --yes` exits with code 4 if there's no active unlock: the
     human manually creates the unlock file in `~/.claude/` and the command is repeated (the
     guardian rule above).
   - `undo` **does not uninstall the superpowers plugin**: it restores `settings.json` to how it
     was, so the plugin stops being enabled but stays downloaded. To remove it entirely, the human
     runs in a terminal:
     `claude plugin uninstall superpowers@superpowers-marketplace --scope user`.
7. **How to change something later:** type the same sentence again
   (`Read <PATH>/general-pipeline/INSTALL_PROMPT.md and follow it`). Claude will start from their
   profile and only ask about what they want to change. The same applies to updating pieces when
   the guide has a new version.

The temporary profile (`P`) is no longer needed: the real copy lives at
`~/.claude/pipeline_profile.json`. Tell them they can delete the temp folder if they want.
