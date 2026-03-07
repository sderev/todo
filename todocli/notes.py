from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

from .config import Config

H2_RE = re.compile(r"^\s*##\s+(?P<title>.+?)\s*$")
H3_RE = re.compile(r"^\s*###\s+(?P<title>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<body>.+?)\s*$")
CARRY_OVER_PREFIX = "Carry-over from "


@dataclass(frozen=True, slots=True)
class PriorNote:
    note_date: date
    path: Path


def note_path_for_date(config: Config, note_date: date) -> Path:
    filename = f"{note_date.isoformat()}.md"
    if config.layout == "flat":
        return config.notes_dir / filename

    return config.notes_dir / f"{note_date:%Y}" / f"{note_date:%m}" / filename


def render_note_header(note_date: date) -> str:
    return f"# {note_date.isoformat()}\n"


def find_latest_note_before(notes_dir: Path, before: date) -> PriorNote | None:
    if not notes_dir.exists():
        return None

    latest: PriorNote | None = None
    for path in notes_dir.rglob("*.md"):
        parsed = parse_note_date(path)
        if parsed is None or parsed >= before:
            continue

        candidate = PriorNote(note_date=parsed, path=path)
        if latest is None or candidate.note_date > latest.note_date:
            latest = candidate

    return latest


def parse_note_date(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return None


def collect_unchecked_tasks(markdown: str) -> dict[str, list[str]]:
    """Return unchecked checkbox items grouped by note section title."""
    grouped: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    current_section = "General"
    in_carry_over_section = False

    for line in markdown.splitlines():
        section_match = H2_RE.match(line)
        if section_match:
            heading = section_match.group("title").strip()
            in_carry_over_section = heading.startswith(CARRY_OVER_PREFIX)
            current_section = "General" if in_carry_over_section else heading
            continue

        if in_carry_over_section:
            subsection_match = H3_RE.match(line)
            if subsection_match:
                current_section = subsection_match.group("title").strip()
                continue

        checkbox_match = CHECKBOX_RE.match(line)
        if checkbox_match is None:
            continue

        mark = checkbox_match.group("mark")
        if mark != " ":
            continue

        body = checkbox_match.group("body").strip()
        key = (current_section, body)
        if key in seen:
            continue

        seen.add(key)
        grouped.setdefault(current_section, []).append(body)

    return grouped


def render_carry_over(previous_date: date, grouped_tasks: dict[str, list[str]]) -> str:
    lines = [f"## Carry-over from {previous_date.isoformat()}", ""]
    for section, tasks in grouped_tasks.items():
        lines.append(f"### {section}")
        for task in tasks:
            lines.append(f"- [ ] {task}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
