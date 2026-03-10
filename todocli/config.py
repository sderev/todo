import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "todo"
DEFAULT_NOTES_DIR = "~/TODO/notes"
DEFAULT_LAYOUT = "year_month"
DEFAULT_CARRY_OVER_MODE = "auto"
DEFAULT_BULLET_MARKER = "*"
ALLOWED_LAYOUTS = {"year_month", "flat"}
ALLOWED_CARRY_OVER_MODES = {"auto", "prompt", "off"}
ALLOWED_BULLET_MARKERS: tuple[str, ...] = ("*", "-")


@dataclass(frozen=True, slots=True)
class Config:
    notes_dir: Path
    layout: str = DEFAULT_LAYOUT
    carry_over_mode: str = DEFAULT_CARRY_OVER_MODE
    bullet_marker: str = DEFAULT_BULLET_MARKER


@dataclass(frozen=True, slots=True)
class ConfigState:
    config: Config
    path: Path
    created: bool = False


def xdg_config_home() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".config"


def config_path() -> Path:
    return xdg_config_home() / APP_NAME / "config.toml"


def default_config() -> Config:
    return Config(notes_dir=Path(DEFAULT_NOTES_DIR).expanduser())


def write_config(path: Path, config: Config) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"notes_dir = {json.dumps(config.notes_dir.as_posix())}\n"
        f"layout = {json.dumps(config.layout)}\n"
        f"carry_over_mode = {json.dumps(config.carry_over_mode)}\n"
        f"bullet_marker = {json.dumps(config.bullet_marker)}\n"
    )
    path.write_text(content, encoding="utf-8")


def _validate_notes_dir(value: object, *, base_dir: Path | None = None) -> Path:
    if not isinstance(value, (str, os.PathLike)):
        raise ValueError(f"Invalid `notes_dir` value: {value!r}. Expected a path string.")

    notes_dir = Path(value).expanduser()
    if notes_dir.is_absolute():
        return notes_dir

    if base_dir is None:
        return notes_dir.resolve()

    return (base_dir / notes_dir).resolve()


def _validate_layout(value: str) -> str:
    if value not in ALLOWED_LAYOUTS:
        allowed = ", ".join(sorted(ALLOWED_LAYOUTS))
        raise ValueError(f"Invalid `layout` value: {value!r}. Expected one of: {allowed}.")
    return value


def _validate_carry_over_mode(value: str) -> str:
    if value not in ALLOWED_CARRY_OVER_MODES:
        allowed = ", ".join(sorted(ALLOWED_CARRY_OVER_MODES))
        raise ValueError(f"Invalid `carry_over_mode` value: {value!r}. Expected one of: {allowed}.")
    return value


def _validate_bullet_marker(value: str) -> str:
    if value not in ALLOWED_BULLET_MARKERS:
        allowed = ", ".join(ALLOWED_BULLET_MARKERS)
        raise ValueError(f"Invalid `bullet_marker` value: {value!r}. Expected one of: {allowed}.")
    return value


def load_config(create_if_missing: bool = True) -> ConfigState:
    path = config_path()
    if not path.exists():
        config = default_config()
        if create_if_missing:
            write_config(path, config)
            return ConfigState(config=config, path=path, created=True)
        return ConfigState(config=config, path=path, created=False)

    data = tomllib.loads(path.read_text(encoding="utf-8"))

    notes_dir = _validate_notes_dir(
        data.get("notes_dir", DEFAULT_NOTES_DIR),
        base_dir=path.parent,
    )
    layout = _validate_layout(data.get("layout", DEFAULT_LAYOUT))
    carry_over_mode = _validate_carry_over_mode(
        data.get("carry_over_mode", DEFAULT_CARRY_OVER_MODE)
    )
    bullet_marker = _validate_bullet_marker(data.get("bullet_marker", DEFAULT_BULLET_MARKER))

    config = Config(
        notes_dir=notes_dir,
        layout=layout,
        carry_over_mode=carry_over_mode,
        bullet_marker=bullet_marker,
    )
    return ConfigState(config=config, path=path, created=False)
