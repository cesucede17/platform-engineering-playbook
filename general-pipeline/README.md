# Personal pipeline guide: your Claude Code setup

This guide installs, **once per person**, the pieces that keep Claude Code working in an orderly
way across all your projects:

| Piece | What it does | Example |
|---|---|---|
| **guardian** | A watchdog that reviews every action Claude takes before it happens and blocks the dangerous ones. | If Claude tries to wipe a project folder outright, or touch the original data in `data/raw`, it gets blocked. |
| **continuity** | When you open Claude Code, it tells you where you left off. | "Last session: yesterday; next step: review the data cleaning." |
| **journal & tasks** | A summary of each day's work and your dated to-do list. | You say "done for today" and a summary is saved; you say "remind me to review the report on Friday" and the task is logged. |
| **`/explain`** | Explains any technical term with an example. | `/explain overfitting` |
| **`/improve-pipeline`** | Extends all of this later on, with review and without breaking anything. | Adding a new tool you saw in another repository. |
| **superpowers** | A required plugin (a skill package) that the improvement process depends on. | — |

Everything adapts to you through a short interview: what you do, how much experience you have
(and therefore how much Claude should explain), which folders are off-limits, what you want to
see when you open Claude...

## Guide order

1. **First, this general guide**, once. It installs into your Claude Code configuration folder
   (`~/.claude`) and applies to every project.
2. **Then, per project**, either `ml-engineering-playbook` (machine learning / data) or
   `platform-engineering-playbook`'s project kit (platforms and web apps). Those guides check
   that the general one is already installed.

## How to install it

1. Open Claude Code, ideally inside your projects folder.
2. Type this (replace `<PATH>` with the folder where the guides live):

   ```text
   Read <PATH>/general_guide/INSTALL_PROMPT.md and follow it
   ```

3. Claude explains how everything is organized and asks about 15 questions, one at a time,
   always with a recommended option (about 10 minutes). If unsure, pick the recommended one.
4. It shows you a summary. **Nothing is installed until you approve it.**
5. It shows which files it will create or change and asks explicit permission for the one
   sensitive change: adding two hooks to `settings.json`, Claude Code's settings file.
6. It installs (after backing up your `~/.claude` first), checks every piece, and gives you a
   report with **OK** or **FAILED** for each.
7. **Close and reopen Claude Code**: you should see the startup summary.

guardian starts in **trial mode** for 7 days: it doesn't block anything (except attempts to touch
its own configuration or create the unlock file), it only logs what it would have blocked. You'll
get a dated task to review that log with Claude and switch it to active mode.

## How to change or update it

Type the same sentence again. Claude sees the pipeline is already installed
(`~/.claude/pipeline_profile.json`), shows your current answers, and asks what you want to
change: just update the pieces to the guide's version, change a few answers, or redo the whole
interview. Your guardian mode (trial or active) is kept.

Since guardian is already installed, this time the installer writes nothing until **you**
manually create the unlock file in `~/.claude/` (Claude will tell you its name; valid for 2
hours). That's the watchdog protecting its own configuration: Claude can never create it for you.

## How to roll back

Ask Claude to undo the installation, or run this yourself in a terminal (from this folder):

```text
python tools/install.py undo         (shows what would happen; changes nothing)
python tools/install.py undo --yes   (does it)
```

- Restores `~/.claude` to how it was before the last install. If you've changed any installed
  file since then, you'll be warned, and a backup of the current state is taken before undoing.
- Since guardian is installed, `undo --yes` also requires that you've manually created the
  unlock file in `~/.claude/` (otherwise it exits without touching anything and tells you so).
- **It does not uninstall the superpowers plugin** (only disables it). To remove it entirely:
  `claude plugin uninstall superpowers@superpowers-marketplace --scope user`.

## Windows and Linux

Works on both (macOS untested).

- Requires **Python 3.10 or later**. Claude detects which one you have: usually `python` or `py`
  on Windows, `python3` on Linux (in the commands above, swap `python` for `python3`).
- Paths use `/` on both systems, Windows included (`C:/Users/<your user>/projects`).
- git is required for projects; Docker only if you use it. If either is missing, Claude warns you
  but the install continues.

## Contents

```
general_guide/
├── README.md             this file
├── INSTALL_PROMPT.md      the prompt Claude follows (the only thing you need to reference)
├── INTERVIEW.md           the interview script and the pipeline_profile.json format
├── tools/                 install.py and its modules (GENERATED, do not hand-edit)
├── components/            guardian, continuity, journal, tasks, /explain, /improve-pipeline (GENERATED)
├── templates/             configs with {{…}} placeholders filled from your profile (GENERATED)
└── VERSION                date and version of the sources it was generated from
```

Folders marked GENERATED come from the original sources through a packager and are not hand-edited:
if a piece is improved, it gets regenerated.
