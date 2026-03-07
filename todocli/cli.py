from datetime import date, datetime, timedelta
from pathlib import Path
from tomllib import TOMLDecodeError

import click
from click_default_group import DefaultGroup

from .config import (
    ALLOWED_CARRY_OVER_MODES,
    ALLOWED_LAYOUTS,
    Config,
    ConfigState,
    DEFAULT_CARRY_OVER_MODE,
    DEFAULT_LAYOUT,
    DEFAULT_NOTES_DIR,
    config_path,
    load_config,
    write_config,
)
from .notes import (
    collect_unchecked_tasks,
    find_latest_note_before,
    note_path_for_date,
    render_carry_over,
    render_note_header,
)


def today_date() -> date:
    return date.today()


def load_config_or_fail(create_if_missing: bool = True) -> ConfigState:
    try:
        return load_config(create_if_missing=create_if_missing)
    except (ValueError, TOMLDecodeError) as exc:
        raise click.ClickException(str(exc)) from exc


def create_or_open_note(
    config: Config,
    note_date: date,
    *,
    carry_enabled: bool,
) -> Path:
    note_path = note_path_for_date(config, note_date)
    created = False

    if not note_path.exists():
        note_path.parent.mkdir(parents=True, exist_ok=True)
        content = render_note_header(note_date) + "\n"
        if carry_enabled:
            carry_over = build_carry_over_section(config=config, note_date=note_date)
            if carry_over:
                content += carry_over

        note_path.write_text(content, encoding="utf-8")
        created = True

    click.edit(filename=str(note_path))
    action = "Created" if created else "Opened"
    click.echo(f"{action}: {note_path}")
    return note_path


def build_carry_over_section(config: Config, note_date: date) -> str:
    if config.carry_over_mode == "off":
        return ""

    prior_note = find_latest_note_before(config.notes_dir, note_date)
    if prior_note is None:
        return ""

    grouped_tasks = collect_unchecked_tasks(prior_note.path.read_text(encoding="utf-8"))
    if not grouped_tasks:
        return ""

    if config.carry_over_mode == "prompt":
        count = sum(len(tasks) for tasks in grouped_tasks.values())
        if not click.confirm(
            f"Carry over {count} unfinished task(s) from {prior_note.note_date.isoformat()}?",
            default=True,
        ):
            return ""

    return render_carry_over(prior_note.note_date, grouped_tasks)


@click.group(name="todo", cls=DefaultGroup, default="today", default_if_no_args=True)
def main() -> None:
    """Create and open dated markdown work notes."""


@main.command()
@click.option(
    "--notes-dir",
    type=click.Path(path_type=Path, dir_okay=True, file_okay=False),
    default=None,
    help="Directory where note files are stored.",
)
@click.option(
    "--layout",
    type=click.Choice(sorted(ALLOWED_LAYOUTS)),
    default=DEFAULT_LAYOUT,
    show_default=True,
)
@click.option(
    "--carry-over-mode",
    type=click.Choice(sorted(ALLOWED_CARRY_OVER_MODES)),
    default=DEFAULT_CARRY_OVER_MODE,
    show_default=True,
)
@click.option("--force", is_flag=True, help="Overwrite an existing config file.")
def init(
    notes_dir: Path | None,
    layout: str,
    carry_over_mode: str,
    force: bool,
) -> None:
    """Create `$XDG_CONFIG_HOME/todo/config.toml` (defaults to `~/.config/todo/config.toml`)."""
    cfg_path = config_path()
    if cfg_path.exists() and not force:
        raise click.ClickException(f"Config already exists at: {cfg_path}")

    resolved_notes_dir = (
        notes_dir.expanduser() if notes_dir is not None else Path(DEFAULT_NOTES_DIR).expanduser()
    )
    resolved_notes_dir = resolved_notes_dir.resolve()
    resolved_notes_dir.mkdir(parents=True, exist_ok=True)

    config = Config(
        notes_dir=resolved_notes_dir,
        layout=layout,
        carry_over_mode=carry_over_mode,
    )
    write_config(cfg_path, config)

    click.echo(f"Config written: {cfg_path}")
    click.echo(f"Notes directory: {resolved_notes_dir}")


@main.command()
@click.option(
    "--no-carry",
    is_flag=True,
    help="Skip carry-over when creating today's note.",
)
def today(no_carry: bool) -> None:
    """Open today's note (default command)."""
    state = load_config_or_fail()
    if state.created:
        state.config.notes_dir.mkdir(parents=True, exist_ok=True)

    create_or_open_note(
        config=state.config,
        note_date=today_date(),
        carry_enabled=not no_carry,
    )


@main.command()
def yesterday() -> None:
    """Open yesterday's note."""
    state = load_config_or_fail()
    target_date = today_date() - timedelta(days=1)
    create_or_open_note(config=state.config, note_date=target_date, carry_enabled=False)


@main.command(name="open")
@click.argument("note_date", type=click.DateTime(formats=["%Y-%m-%d"]))
def open_note(note_date: datetime) -> None:
    """Open note for `YYYY-MM-DD` (create if missing)."""
    state = load_config_or_fail()
    target = note_date.date()
    allow_carry = target == today_date()
    create_or_open_note(config=state.config, note_date=target, carry_enabled=allow_carry)


@main.command(name="config")
def show_config() -> None:
    """Show effective config values."""
    state = load_config_or_fail(create_if_missing=False)
    click.echo(f"Config file: {state.path}")
    if not state.path.exists():
        click.echo("(file does not exist yet; showing defaults)")
    click.echo(f"notes_dir: {state.config.notes_dir}")
    click.echo(f"layout: {state.config.layout}")
    click.echo(f"carry_over_mode: {state.config.carry_over_mode}")


if __name__ == "__main__":
    main()
