# `todo`

`todo` is a small CLI to create and open daily markdown notes.

When a new note is created for today, the CLI can copy unfinished checkbox tasks from the latest previous note.

## Install from GitHub

```bash
uv tool install --force git+https://github.com/sderev/todo
```

## Run From A Clone

Use the repo-local wrapper:

```bash
./todo --help
```

It delegates to `uv run --project <repo-root> python -m todocli`, so it still works when you run `./todo` from outside the repo root.

## Python Version

* Python 3.13+

## Commands

* `todo`
  * Default command.
  * Open today's note (create it if missing).
* `todo today`
  * Same as `todo`.
* `todo today --no-carry`
  * Create/open today's note without carry-over.
* `todo yesterday`
  * Open yesterday's note (create if missing).
* `todo open YYYY-MM-DD`
  * Open a specific date note (create if missing).
* `todo init`
  * Create config file and notes directory.
* `todo config`
  * Show effective config values.

## Shell Completion

Completion files are generated from Click 8 shell-completion support.

* Bash: `completion/_todo_completion.bash`
* Zsh: `completion/_todo_completion.zsh`

Regenerate them:

```bash
_TODO_COMPLETE=bash_source ./todo > completion/_todo_completion.bash
_TODO_COMPLETE=zsh_source ./todo > completion/_todo_completion.zsh
```

Load from your shell config:

* Bash (`~/.bashrc`): `source /path/to/repo/completion/_todo_completion.bash`
* Zsh (`~/.zshrc`): `source /path/to/repo/completion/_todo_completion.zsh`

## Config File

Path:

* `$XDG_CONFIG_HOME/todo/config.toml` (defaults to `~/.config/todo/config.toml`)

Example:

```toml
notes_dir = "~/TODO/notes"
layout = "year_month"
carry_over_mode = "auto"
```

Fields:

* `notes_dir`
  * Base folder for notes.
  * `todo init` stores it as an absolute path, so later commands do not depend on the current working directory.
* `layout`
  * `year_month` or `flat`.
  * `year_month` stores notes in `YYYY/MM/YYYY-MM-DD.md`.
* `carry_over_mode`
  * `auto`: always copy unfinished tasks from latest previous note.
  * `prompt`: ask for confirmation before copying.
  * `off`: never copy unfinished tasks.

## Carry-over Rules

When `todo` creates today's note:

* It finds the latest previous note by date (not strictly yesterday).
* It extracts markdown checkboxes with unchecked mark: `- [ ] ...`.
* It ignores checked boxes: `- [x] ...` and `- [X] ...`.
* It keeps section context from note headings (`## ...`) and carried subsections (`### ...`).
* It preserves original section names when a carry-over section is carried again on a later day.
* Tasks that appear before any section heading are grouped under a `General` section.
* It writes a `## Carry-over from YYYY-MM-DD` section in today's note.

## Development

Install deps:

```bash
uv sync --extra dev
```

Run tests:

```bash
uv run pytest
```
