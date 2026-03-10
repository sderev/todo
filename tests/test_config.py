from pathlib import Path

import pytest

from todocli.config import Config, config_path, load_config, write_config


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    home = tmp_path / "home"
    xdg = tmp_path / "xdg"
    home.mkdir()
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return {"home": home, "xdg": xdg}


def test_load_config_without_create_returns_defaults(
    isolated_home: dict[str, Path],
) -> None:
    state = load_config(create_if_missing=False)

    assert state.created is False
    assert state.path == isolated_home["xdg"] / "todo" / "config.toml"
    assert not state.path.exists()
    assert state.config.notes_dir == isolated_home["home"] / "TODO" / "notes"
    assert state.config.layout == "year_month"
    assert state.config.carry_over_mode == "auto"
    assert state.config.bullet_marker == "*"


def test_load_config_rejects_invalid_layout(
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        'notes_dir = "~/TODO/notes"\nlayout = "invalid"\ncarry_over_mode = "auto"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid `layout` value"):
        load_config()


def test_load_config_rejects_invalid_carry_over_mode(
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        'notes_dir = "~/TODO/notes"\nlayout = "year_month"\ncarry_over_mode = "maybe"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid `carry_over_mode` value"):
        load_config()


def test_load_config_rejects_invalid_bullet_marker(
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        'notes_dir = "~/TODO/notes"\nlayout = "year_month"\ncarry_over_mode = "auto"\n'
        'bullet_marker = "+"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid `bullet_marker` value"):
        load_config()


def test_load_config_rejects_invalid_notes_dir_type(
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        'notes_dir = 12\nlayout = "year_month"\ncarry_over_mode = "auto"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid `notes_dir` value"):
        load_config()


def test_write_config_escapes_quoted_notes_dir(
    isolated_home: dict[str, Path],
) -> None:
    cfg_path = config_path()
    notes_dir = isolated_home["home"] / 'notes"quoted'

    write_config(
        cfg_path,
        Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto"),
    )

    assert '\\"' in cfg_path.read_text(encoding="utf-8")
    state = load_config()
    assert state.config.notes_dir == notes_dir
