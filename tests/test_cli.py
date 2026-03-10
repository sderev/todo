import os
import subprocess
from datetime import date
from pathlib import Path

import pytest
from click.testing import CliRunner

from todocli import cli
from todocli.config import Config
from todocli.config import write_config as write_app_config
from todocli.notes import note_path_for_date


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    home = tmp_path / "home"
    xdg = tmp_path / "xdg"
    home.mkdir()
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return {"home": home, "xdg": xdg}


@pytest.fixture
def fake_editor(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    opened: list[Path] = []

    def _edit(*, filename: str):
        opened.append(Path(filename))
        return None

    monkeypatch.setattr(cli.click, "edit", _edit)
    return opened


def write_config(
    path: Path,
    *,
    notes_dir: Path,
    layout: str,
    carry_over_mode: str,
    bullet_marker: str = "*",
) -> None:
    write_app_config(
        path,
        Config(
            notes_dir=notes_dir,
            layout=layout,
            carry_over_mode=carry_over_mode,
            bullet_marker=bullet_marker,
        ),
    )


def test_default_command_creates_today_note(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, [])

    assert result.exit_code == 0
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    assert cfg_path.exists()

    note_path = isolated_home["home"] / "TODO" / "notes" / "2026" / "03" / "2026-03-09.md"
    assert note_path.exists()
    assert note_path.read_text(encoding="utf-8").startswith("# 2026-03-09")
    assert fake_editor == [note_path]


def test_today_carries_from_latest_previous_note(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    old_note = note_path_for_date(config, date(2026, 3, 5))
    old_note.parent.mkdir(parents=True, exist_ok=True)
    old_note.write_text("# 2026-03-05\n\n## Legacy\n- [ ] stale task\n", encoding="utf-8")

    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text(
        """# 2026-03-06

## Network migration
- [ ] Finish change plan
- [X] Announce completion

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")

    assert "## Carry-over from 2026-03-06" in content
    assert "* [ ] Finish change plan" in content
    assert "* [ ] Reply to NOC" in content
    assert "Announce completion" not in content
    assert "stale task" not in content
    assert fake_editor == [today_note]


def test_today_carries_from_bare_checkbox_items(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    prior_note = note_path_for_date(config, date(2026, 3, 5))
    prior_note.parent.mkdir(parents=True, exist_ok=True)
    prior_note.write_text(
        """# 2026-03-05

## first
[ ] a
[ ] b
[ ] c

## second
[ ] d
[x] e
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 7))

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 7))
    content = today_note.read_text(encoding="utf-8")

    assert "## Carry-over from 2026-03-05" in content
    assert "* [ ] a" in content
    assert "* [ ] b" in content
    assert "* [ ] c" in content
    assert "* [ ] d" in content
    assert "* [ ] e" not in content
    assert fake_editor == [today_note]


def test_today_preserves_section_context_across_multiple_carry_overs(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text(
        """# 2026-03-06

## Network migration
- [ ] Finish change plan

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    first_result = runner.invoke(cli.main, ["today"])

    assert first_result.exit_code == 0
    monday_note = note_path_for_date(config, date(2026, 3, 9))
    assert "### Network migration" in monday_note.read_text(encoding="utf-8")
    fake_editor.clear()

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 10))
    second_result = runner.invoke(cli.main, ["today"])

    assert second_result.exit_code == 0
    tuesday_note = note_path_for_date(config, date(2026, 3, 10))
    content = tuesday_note.read_text(encoding="utf-8")

    assert "## Carry-over from 2026-03-09" in content
    assert "### Network migration" in content
    assert "### Tickets" in content
    assert "### Carry-over from 2026-03-06" not in content
    assert fake_editor == [tuesday_note]


def test_today_no_carry_flag_skips_copy(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["today", "--no-carry"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "Carry-over" not in content
    assert fake_editor == [today_note]


def test_prompt_mode_respects_confirmation(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="prompt")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="prompt")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    monkeypatch.setattr(cli.click, "confirm", lambda *args, **kwargs: False)

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "Carry-over" not in content
    assert fake_editor == [today_note]


def test_prompt_mode_carries_when_confirmed(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="prompt")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="prompt")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    monkeypatch.setattr(cli.click, "confirm", lambda *args, **kwargs: True)

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "Carry-over" in content
    assert "* [ ] Pending task" in content
    assert fake_editor == [today_note]


def test_off_mode_skips_carry_over(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="off")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="off")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "Carry-over" not in content
    assert fake_editor == [today_note]


def test_yesterday_creates_previous_day_note(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["yesterday"])

    assert result.exit_code == 0
    yesterday_note = note_path_for_date(config, date(2026, 3, 8))
    assert yesterday_note.exists()
    assert fake_editor == [yesterday_note]


def test_init_resolves_relative_notes_dir_once(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = isolated_home["home"] / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    init_result = runner.invoke(cli.main, ["init", "--notes-dir", "notes"])

    assert init_result.exit_code == 0
    expected_notes_dir = workspace / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    assert f'notes_dir = "{expected_notes_dir.as_posix()}"' in cfg_path.read_text(encoding="utf-8")

    elsewhere = isolated_home["home"] / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    today_result = runner.invoke(cli.main, ["today"])

    assert today_result.exit_code == 0
    today_note = expected_notes_dir / "2026" / "03" / "2026-03-09.md"
    assert today_note.exists()
    assert fake_editor == [today_note]
    assert not (elsewhere / "notes").exists()


def test_init_supports_quoted_notes_dir(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = isolated_home["home"] / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    init_result = runner.invoke(cli.main, ["init", "--notes-dir", 'notes"quoted'])

    assert init_result.exit_code == 0
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    config_text = cfg_path.read_text(encoding="utf-8")
    assert '\\"' in config_text

    elsewhere = isolated_home["home"] / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    today_result = runner.invoke(cli.main, ["today"])

    assert today_result.exit_code == 0
    today_note = workspace / 'notes"quoted' / "2026" / "03" / "2026-03-09.md"
    assert today_note.exists()
    assert fake_editor == [today_note]


def test_open_non_today_skips_carry_over(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["open", "2026-03-08"])

    assert result.exit_code == 0
    target_note = note_path_for_date(config, date(2026, 3, 8))
    content = target_note.read_text(encoding="utf-8")
    assert "Carry-over" not in content
    assert fake_editor == [target_note]


def test_today_keeps_existing_file_unchanged(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    existing_today = note_path_for_date(config, date(2026, 3, 9))
    existing_today.parent.mkdir(parents=True, exist_ok=True)
    existing_today.write_text("# 2026-03-09\n\nmanual content\n", encoding="utf-8")

    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    assert existing_today.read_text(encoding="utf-8") == "# 2026-03-09\n\nmanual content\n"
    assert fake_editor == [existing_today]


def test_config_command_shows_defaults_without_file(
    runner: CliRunner,
    isolated_home: dict[str, Path],
) -> None:
    result = runner.invoke(cli.main, ["config"])

    assert result.exit_code == 0
    assert "(file does not exist yet; showing defaults)" in result.output
    assert str(isolated_home["home"] / "TODO" / "notes") in result.output
    assert "layout: year_month" in result.output
    assert "carry_over_mode: auto" in result.output
    assert "bullet_marker: *" in result.output


def test_repo_wrapper_runs_without_traceback(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper = repo_root / "todo"
    home = tmp_path / "home"
    xdg = tmp_path / "xdg"
    workdir = tmp_path / "workdir"
    home.mkdir()
    xdg.mkdir()
    workdir.mkdir()

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(xdg)

    result = subprocess.run(
        [str(wrapper), "--help"],
        capture_output=True,
        check=False,
        cwd=workdir,
        env=env,
        text=True,
    )

    assert result.returncode == 0
    assert "Create and open dated markdown work notes." in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_supports_version_option(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["--version"])

    assert result.exit_code == 0
    assert result.output.startswith("todo, version ")


def test_init_help_mentions_default_config_location(runner: CliRunner) -> None:
    result = runner.invoke(cli.main, ["init", "--help"])

    assert result.exit_code == 0
    help_text = " ".join(result.output.split())
    assert (
        "Create `~/.config/todo/config.toml` (or `$XDG_CONFIG_HOME/todo/config.toml` if set)."
    ) in help_text


def test_config_command_rejects_invalid_notes_dir_type(
    runner: CliRunner,
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        'notes_dir = 12\nlayout = "year_month"\ncarry_over_mode = "auto"\n',
        encoding="utf-8",
    )

    result = runner.invoke(cli.main, ["config"])

    assert result.exit_code != 0
    assert "Error: Invalid `notes_dir` value" in result.output
    assert "Traceback" not in result.output


def test_catchup_dry_run_prints_grouped_preview_without_creating_today_note(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

## Ops
- [ ] Update package index
""",
        encoding="utf-8",
    )

    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Ops
- [x] Update package index

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["catchup", "--since", "2026-03-05", "--dry-run"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    assert not today_note.exists()
    assert "Target note:" in result.output
    assert "Would import:" in result.output
    assert "### Tickets" in result.output
    assert "* [ ] Reply to NOC" in result.output
    assert "Update package index" not in result.output
    assert "Scanned files: 2" in result.output
    assert "Unresolved tasks: 1" in result.output
    assert "Date range: 2026-03-05..2026-03-06" in result.output
    assert fake_editor == []


def test_catchup_large_scan_can_cancel_with_confirmation_prompt(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    for note_day in (date(2026, 3, 5), date(2026, 3, 6)):
        note_path = note_path_for_date(config, note_day)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("# note\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    monkeypatch.setattr(cli, "CATCHUP_CONFIRM_THRESHOLD", 1)

    prompted: dict[str, object] = {}

    def _confirm(text: str, default: bool = False) -> bool:
        prompted["text"] = text
        prompted["default"] = default
        return False

    monkeypatch.setattr(cli.click, "confirm", _confirm)

    result = runner.invoke(cli.main, ["catchup"])

    assert result.exit_code == 0
    assert "Cancelled." in result.output
    assert prompted["default"] is False
    assert "About to scan 2 dated note file(s). Continue?" in str(prompted["text"])

    today_note = note_path_for_date(config, date(2026, 3, 9))
    assert not today_note.exists()
    assert fake_editor == []


def test_catchup_yes_skips_large_scan_confirmation(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    for note_day in (date(2026, 3, 5), date(2026, 3, 6)):
        note_path = note_path_for_date(config, note_day)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text("# note\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    monkeypatch.setattr(cli, "CATCHUP_CONFIRM_THRESHOLD", 1)

    def _fail_confirm(*args, **kwargs):
        raise AssertionError("confirm should be skipped when --yes is set")

    monkeypatch.setattr(cli.click, "confirm", _fail_confirm)

    result = runner.invoke(cli.main, ["catchup", "--yes", "--dry-run"])

    assert result.exit_code == 0
    assert "Scanned files: 2" in result.output
    assert fake_editor == []


def test_catchup_upserts_managed_section_and_opens_today_note(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

## Ops
- [ ] Update package index
""",
        encoding="utf-8",
    )

    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Carry-over from 2026-03-05

### Ops
- [x] Update package index

### Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    today_note = note_path_for_date(config, date(2026, 3, 9))
    today_note.parent.mkdir(parents=True, exist_ok=True)
    today_note.write_text(
        """# 2026-03-09

Manual note

<!-- todo catchup start -->
## Catch-up

### Ops
- [ ] stale task
<!-- todo catchup end -->
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["catchup"])

    assert result.exit_code == 0
    content = today_note.read_text(encoding="utf-8")
    assert content.count("<!-- todo catchup start -->") == 1
    assert "stale task" not in content
    assert "Manual note" in content
    assert "### Tickets" in content
    assert "* [ ] Reply to NOC" in content
    assert "Update package index" not in content
    assert fake_editor == [today_note]
    assert "Updated:" in result.output
    assert "Scanned files: 2" in result.output
    assert "Unresolved tasks: 1" in result.output


def test_catchup_without_unresolved_tasks_removes_managed_section(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(cfg_path, notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")
    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

## Ops
- [ ] Update package index
""",
        encoding="utf-8",
    )

    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Ops
- [x] Update package index
""",
        encoding="utf-8",
    )

    today_note = note_path_for_date(config, date(2026, 3, 9))
    today_note.parent.mkdir(parents=True, exist_ok=True)
    today_note.write_text(
        """# 2026-03-09

Manual note

<!-- todo catchup start -->
## Catch-up

### Ops
- [ ] stale task
<!-- todo catchup end -->
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["catchup"])

    assert result.exit_code == 0
    content = today_note.read_text(encoding="utf-8")
    assert "<!-- todo catchup start -->" not in content
    assert "stale task" not in content
    assert "Manual note" in content
    assert fake_editor == [today_note]
    assert "Unresolved tasks: 0" in result.output


# ---------------------------------------------------------------------------
# bullet_marker tests
# ---------------------------------------------------------------------------


def test_config_command_shows_configured_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(
        cfg_path,
        notes_dir=notes_dir,
        layout="year_month",
        carry_over_mode="auto",
        bullet_marker="-",
    )

    result = runner.invoke(cli.main, ["config"])

    assert result.exit_code == 0
    assert "bullet_marker: -" in result.output


def test_init_writes_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    init_result = runner.invoke(cli.main, ["init", "--bullet-marker", "-"])

    assert init_result.exit_code == 0
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    assert 'bullet_marker = "-"' in cfg_path.read_text(encoding="utf-8")

    config_result = runner.invoke(cli.main, ["config"])
    assert "bullet_marker: -" in config_result.output


def test_init_rejects_invalid_bullet_marker_choice(
    runner: CliRunner,
    isolated_home: dict[str, Path],
) -> None:
    result = runner.invoke(cli.main, ["init", "--bullet-marker", "+"])

    assert result.exit_code != 0
    assert "Invalid value for '--bullet-marker'" in result.output


def test_today_carries_from_latest_previous_note_with_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(
        cfg_path,
        notes_dir=notes_dir,
        layout="year_month",
        carry_over_mode="auto",
        bullet_marker="-",
    )

    config = Config(
        notes_dir=notes_dir, layout="year_month", carry_over_mode="auto", bullet_marker="-"
    )
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text(
        """# 2026-03-06

## Tickets
- [ ] Reply to NOC
- [X] Closed task
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "- [ ] Reply to NOC" in content
    assert "Closed task" not in content
    assert fake_editor == [today_note]


def test_prompt_mode_carries_when_confirmed_with_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(
        cfg_path,
        notes_dir=notes_dir,
        layout="year_month",
        carry_over_mode="prompt",
        bullet_marker="-",
    )

    config = Config(
        notes_dir=notes_dir, layout="year_month", carry_over_mode="prompt", bullet_marker="-"
    )
    friday_note = note_path_for_date(config, date(2026, 3, 6))
    friday_note.parent.mkdir(parents=True, exist_ok=True)
    friday_note.write_text("# 2026-03-06\n\n## Ops\n- [ ] Pending task\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))
    monkeypatch.setattr(cli.click, "confirm", lambda *args, **kwargs: True)

    result = runner.invoke(cli.main, ["today"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    content = today_note.read_text(encoding="utf-8")
    assert "Carry-over" in content
    assert "- [ ] Pending task" in content
    assert fake_editor == [today_note]


def test_catchup_dry_run_uses_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(
        cfg_path,
        notes_dir=notes_dir,
        layout="year_month",
        carry_over_mode="auto",
        bullet_marker="-",
    )

    config = Config(
        notes_dir=notes_dir, layout="year_month", carry_over_mode="auto", bullet_marker="-"
    )
    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["catchup", "--since", "2026-03-06", "--dry-run"])

    assert result.exit_code == 0
    today_note = note_path_for_date(config, date(2026, 3, 9))
    assert not today_note.exists()
    assert "- [ ] Reply to NOC" in result.output
    assert fake_editor == []


def test_catchup_upserts_managed_section_with_dash_bullet_marker(
    runner: CliRunner,
    isolated_home: dict[str, Path],
    fake_editor: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    notes_dir = isolated_home["home"] / "notes"
    cfg_path = isolated_home["xdg"] / "todo" / "config.toml"
    write_config(
        cfg_path,
        notes_dir=notes_dir,
        layout="year_month",
        carry_over_mode="auto",
        bullet_marker="-",
    )

    config = Config(
        notes_dir=notes_dir, layout="year_month", carry_over_mode="auto", bullet_marker="-"
    )
    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    today_note = note_path_for_date(config, date(2026, 3, 9))
    today_note.parent.mkdir(parents=True, exist_ok=True)
    today_note.write_text("# 2026-03-09\n\nManual note\n", encoding="utf-8")

    monkeypatch.setattr(cli, "today_date", lambda: date(2026, 3, 9))

    result = runner.invoke(cli.main, ["catchup", "--since", "2026-03-06"])

    assert result.exit_code == 0
    content = today_note.read_text(encoding="utf-8")
    assert "- [ ] Reply to NOC" in content
    assert "* [ ] Reply to NOC" not in content
    assert "Manual note" in content
    assert fake_editor == [today_note]
