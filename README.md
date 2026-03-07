# `todo`

A CLI that creates and opens daily markdown notes. When a new note is
created, it can carry over unfinished checkbox tasks from the previous note.

## Install

```bash
uv tool install --force git+https://github.com/sderev/todo
```

Requires Python 3.13+.

## Quick start

```bash
todo init                        # create config + notes directory
todo                             # open today's note in $EDITOR
```

On first run without `init`, `todo` creates a default config at
`~/.config/todo/config.toml` (or `$XDG_CONFIG_HOME/todo/config.toml` if set)
and stores notes under `~/TODO/notes/`.

## Usage

```bash
todo                             # open today's note (create if missing)
todo today                       # same as above
todo today --no-carry            # skip carry-over of unfinished tasks
todo yesterday                   # open yesterday's note
todo open 2026-03-05             # open a specific date's note
todo catchup                     # rebuild Catch-up section in today's note
todo catchup --since 2026-01-01  # limit scan start date (inclusive)
todo catchup --dry-run           # preview what would be imported
todo catchup --yes               # skip long-scan confirmation
todo config                      # show current config values
```

### Carry-over

When `todo` creates a new note, it looks for the latest previous note (by
date, not strictly yesterday) and copies unchecked checkboxes (`- [ ] ...`)
into a `## Carry-over from YYYY-MM-DD` section. Checked boxes are ignored.

Section context (`## ...` headings) is preserved. Tasks before any heading
are grouped under `General`. When a carry-over section is carried again on a
later day, the original section names are kept.

Controlled by the `carry_over_mode` config key:

* `auto` -- always copy (default).
* `prompt` -- ask before copying.
* `off` -- never copy.

The `--no-carry` flag on `todo today` overrides any mode for that invocation.

### Catch-up

`todo catchup` scans all dated notes before today, tracks the latest checkbox
state for each task, and imports only tasks whose latest state is unchecked.
It writes a managed `## Catch-up` section (fenced by HTML comments) so
rerunning is idempotent.

`--dry-run` prints the grouped tasks and a summary (scanned files count,
unresolved tasks count, date range) without changing today's note.

If the scan would process many files (more than 500), `todo catchup` asks
for confirmation. Use `--yes` to skip that prompt.

## Config

Location: `~/.config/todo/config.toml` by default.

If `XDG_CONFIG_HOME` is set, `todo` uses
`$XDG_CONFIG_HOME/todo/config.toml`.

```toml
notes_dir = "~/TODO/notes"
layout = "year_month"
carry_over_mode = "auto"
```

| Key                | Values                      | Effect                                         |
|--------------------|-----------------------------|-------------------------------------------------|
| `notes_dir`        | any path                    | Base folder for notes. Stored as absolute path. |
| `layout`           | `year_month`, `flat`        | `year_month` stores notes in `YYYY/MM/`.        |
| `carry_over_mode`  | `auto`, `prompt`, `off`     | See [Carry-over](#carry-over) above.            |

## Shell completion

Completion files live in `completion/` and are generated from Click:

```bash
_TODO_COMPLETE=bash_source ./todo > completion/_todo_completion.bash
_TODO_COMPLETE=zsh_source  ./todo > completion/_todo_completion.zsh
```

Source the relevant file from your shell config:

```bash
# Bash (~/.bashrc)
source /path/to/repo/completion/_todo_completion.bash

# Zsh (~/.zshrc)
source /path/to/repo/completion/_todo_completion.zsh
```

## Development

```bash
uv sync --extra dev   # install deps
uv run pytest          # run tests
```

The repo-local `./todo` wrapper delegates to `uv run --project <repo-root>
python -m todocli`, so it works from any directory.
