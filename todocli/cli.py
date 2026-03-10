from datetime import date, datetime, timedelta
from pathlib import Path
from tomllib import TOMLDecodeError

import click
from click_default_group import DefaultGroup

from .config import (
    ALLOWED_BULLET_MARKERS,
    ALLOWED_CARRY_OVER_MODES,
    ALLOWED_LAYOUTS,
    DEFAULT_BULLET_MARKER,
    DEFAULT_CARRY_OVER_MODE,
    DEFAULT_LAYOUT,
    DEFAULT_NOTES_DIR,
    Config,
    ConfigState,
    config_path,
    load_config,
    write_config,
)
from .notes import (
    collect_unchecked_tasks,
    find_latest_note_before,
    list_dated_notes,
    note_path_for_date,
    render_carry_over,
    render_catchup_block,
    render_note_header,
    replace_catchup_block,
    scan_catchup_tasks_from_notes,
)

CATCHUP_CONFIRM_THRESHOLD = 500
ACTION_COLORS = {
    "Created": "green",
    "Updated": "yellow",
    "Opened": "cyan",
}


def styled_label(label: str) -> str:
    return click.style(label, bold=True)


def emit_action(action: str, path: Path) -> None:
    click.echo(f"{click.style(action, fg=ACTION_COLORS[action], bold=True)}: {path}")


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
    emit_action(action, note_path)
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

    return render_carry_over(
        prior_note.note_date,
        grouped_tasks,
        bullet_marker=config.bullet_marker,
    )


def format_catchup_preview(grouped_tasks: dict[str, list[str]], *, bullet_marker: str) -> str:
    lines = ["Would import:"]
    for section, tasks in grouped_tasks.items():
        lines.append(f"### {section}")
        lines.append("")
        for task in tasks:
            lines.append(f"{bullet_marker} [ ] {task}")
        lines.append("")

    return "\n".join(lines).rstrip()


def format_scan_range(start: date | None, end: date | None) -> str:
    if start is None or end is None:
        return "none"
    return f"{start.isoformat()}..{end.isoformat()}"


def print_catchup_summary(
    *,
    scanned_files_count: int,
    unresolved_tasks_count: int,
    scanned_start: date | None,
    scanned_end: date | None,
) -> None:
    click.echo(f"{styled_label('Scanned files')}: {scanned_files_count}")
    click.echo(f"{styled_label('Unresolved tasks')}: {unresolved_tasks_count}")
    click.echo(f"{styled_label('Date range')}: {format_scan_range(scanned_start, scanned_end)}")


def create_or_update_catchup_note(
    config: Config,
    note_date: date,
    grouped_tasks: dict[str, list[str]],
) -> Path:
    note_path = note_path_for_date(config, note_date)
    note_path.parent.mkdir(parents=True, exist_ok=True)

    existed = note_path.exists()
    original_content = (
        note_path.read_text(encoding="utf-8") if existed else render_note_header(note_date) + "\n"
    )
    catchup_block = (
        render_catchup_block(grouped_tasks, bullet_marker=config.bullet_marker)
        if grouped_tasks
        else None
    )
    updated_content = replace_catchup_block(original_content, catchup_block)

    if not existed or updated_content != original_content:
        note_path.write_text(updated_content, encoding="utf-8")

    click.edit(filename=str(note_path))
    if not existed:
        action = "Created"
    elif updated_content != original_content:
        action = "Updated"
    else:
        action = "Opened"
    emit_action(action, note_path)
    return note_path


@click.group(name="todo", cls=DefaultGroup, default="today", default_if_no_args=True)
@click.version_option(package_name="todo-daily-notes")
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
    help="Directory structure for note files.",
)
@click.option(
    "--carry-over-mode",
    type=click.Choice(sorted(ALLOWED_CARRY_OVER_MODES)),
    default=DEFAULT_CARRY_OVER_MODE,
    show_default=True,
    help="How to handle unfinished tasks from the previous note.",
)
@click.option(
    "--bullet-marker",
    type=click.Choice(ALLOWED_BULLET_MARKERS),
    default=DEFAULT_BULLET_MARKER,
    show_default=True,
    help="Bullet marker used for checkbox list items.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing config file.")
def init(
    notes_dir: Path | None,
    layout: str,
    carry_over_mode: str,
    bullet_marker: str,
    force: bool,
) -> None:
    """Create `~/.config/todo/config.toml` (or `$XDG_CONFIG_HOME/todo/config.toml` if set)."""
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
        bullet_marker=bullet_marker,
    )
    write_config(cfg_path, config)

    click.echo(f"{styled_label('Config written')}: {cfg_path}")
    click.echo(f"{styled_label('Notes directory')}: {resolved_notes_dir}")


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
    click.echo(f"{styled_label('Config file')}: {state.path}")
    if not state.path.exists():
        click.echo(click.style("(file does not exist yet; showing defaults)", fg="yellow"))
    click.echo(f"{styled_label('notes_dir')}: {state.config.notes_dir}")
    click.echo(f"{styled_label('layout')}: {state.config.layout}")
    click.echo(f"{styled_label('carry_over_mode')}: {state.config.carry_over_mode}")
    click.echo(f"{styled_label('bullet_marker')}: {state.config.bullet_marker}")


@main.command()
@click.option(
    "--since",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Limit scan start date (inclusive).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be imported without editing today's note.",
)
@click.option(
    "--yes",
    is_flag=True,
    help=(f"Skip confirmation when scanning many files (more than {CATCHUP_CONFIRM_THRESHOLD})."),
)
def catchup(since: datetime | None, dry_run: bool, yes: bool) -> None:
    """Recover unresolved tasks from historical notes into today's note."""
    state = load_config_or_fail()
    target_date = today_date()
    since_date = since.date() if since is not None else None

    notes = list_dated_notes(
        state.config.notes_dir,
        before=target_date,
        since=since_date,
    )
    if len(notes) > CATCHUP_CONFIRM_THRESHOLD and not yes:
        if not click.confirm(
            (f"About to scan {len(notes)} dated note file(s). Continue?"),
            default=False,
        ):
            click.secho("Cancelled.", fg="yellow", bold=True)
            return

    scan_result = scan_catchup_tasks_from_notes(notes)
    unresolved_tasks_count = sum(len(tasks) for tasks in scan_result.grouped_tasks.values())

    if dry_run:
        click.echo(
            f"{styled_label('Target note')}: {note_path_for_date(state.config, target_date)}"
        )
        if scan_result.grouped_tasks:
            click.echo(
                format_catchup_preview(
                    scan_result.grouped_tasks,
                    bullet_marker=state.config.bullet_marker,
                )
            )
        else:
            click.echo(f"{styled_label('Would import')}: nothing")

        print_catchup_summary(
            scanned_files_count=scan_result.scanned_files_count,
            unresolved_tasks_count=unresolved_tasks_count,
            scanned_start=scan_result.scanned_start,
            scanned_end=scan_result.scanned_end,
        )
        return

    create_or_update_catchup_note(
        config=state.config,
        note_date=target_date,
        grouped_tasks=scan_result.grouped_tasks,
    )
    print_catchup_summary(
        scanned_files_count=scan_result.scanned_files_count,
        unresolved_tasks_count=unresolved_tasks_count,
        scanned_start=scan_result.scanned_start,
        scanned_end=scan_result.scanned_end,
    )


if __name__ == "__main__":
    main()
