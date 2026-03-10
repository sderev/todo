import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import Config

H2_RE = re.compile(r"^\s*##\s+(?P<title>.+?)\s*$")
H3_RE = re.compile(r"^\s*###\s+(?P<title>.+?)\s*$")
CHECKBOX_RE = re.compile(r"^\s*(?:[-*]\s+)?\[(?P<mark>[ xX])\]\s+(?P<body>.+?)\s*$")
CARRY_OVER_PREFIX = "Carry-over from "
CATCHUP_START_MARKER = "<!-- todo catchup start -->"
CATCHUP_END_MARKER = "<!-- todo catchup end -->"


@dataclass(frozen=True, slots=True)
class PriorNote:
    note_date: date
    path: Path


@dataclass(frozen=True, slots=True)
class CheckboxEntry:
    section: str
    body: str
    checked: bool


@dataclass(frozen=True, slots=True)
class CatchupScanResult:
    scanned_files_count: int
    grouped_tasks: dict[str, list[str]]
    scanned_start: date | None
    scanned_end: date | None


def note_path_for_date(config: Config, note_date: date) -> Path:
    filename = f"{note_date.isoformat()}.md"
    if config.layout == "flat":
        return config.notes_dir / filename

    return config.notes_dir / f"{note_date:%Y}" / f"{note_date:%m}" / filename


def render_note_header(note_date: date) -> str:
    return f"# {note_date.isoformat()}\n"


def find_latest_note_before(notes_dir: Path, before: date) -> PriorNote | None:
    notes = list_dated_notes(notes_dir, before=before)
    if not notes:
        return None

    return notes[-1]


def parse_note_date(path: Path) -> date | None:
    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return None


def list_dated_notes(
    notes_dir: Path, *, before: date, since: date | None = None
) -> list[PriorNote]:
    if not notes_dir.exists():
        return []

    notes: list[PriorNote] = []
    for path in notes_dir.rglob("*.md"):
        parsed = parse_note_date(path)
        if parsed is None or parsed >= before:
            continue
        if since is not None and parsed < since:
            continue
        notes.append(PriorNote(note_date=parsed, path=path))

    return sorted(notes, key=lambda note: (note.note_date, note.path.as_posix()))


def iter_checkbox_entries(markdown: str) -> list[CheckboxEntry]:
    entries: list[CheckboxEntry] = []
    current_section = "General"
    in_carry_over_section = False
    in_catchup_block = False

    for line in markdown.splitlines():
        stripped_line = line.strip()
        if stripped_line == CATCHUP_START_MARKER:
            in_catchup_block = True
            in_carry_over_section = False
            current_section = "General"
            continue

        if stripped_line == CATCHUP_END_MARKER:
            in_catchup_block = False
            in_carry_over_section = False
            current_section = "General"
            continue

        section_match = H2_RE.match(line)
        if section_match:
            heading = section_match.group("title").strip()
            if in_catchup_block and heading == "Catch-up":
                in_carry_over_section = False
                current_section = "General"
                continue

            in_carry_over_section = heading.startswith(CARRY_OVER_PREFIX)
            current_section = "General" if in_carry_over_section else heading
            continue

        if in_carry_over_section or in_catchup_block:
            subsection_match = H3_RE.match(line)
            if subsection_match:
                current_section = subsection_match.group("title").strip()
                continue

        checkbox_match = CHECKBOX_RE.match(line)
        if checkbox_match is None:
            continue

        entries.append(
            CheckboxEntry(
                section=current_section,
                body=checkbox_match.group("body").strip(),
                checked=checkbox_match.group("mark") != " ",
            )
        )

    return entries


def collect_unchecked_tasks(markdown: str) -> dict[str, list[str]]:
    """Return unchecked checkbox items grouped by note section title.

    Latest checkbox state wins per task body within the note.
    """
    latest_states: dict[str, tuple[str, bool, int]] = {}

    for index, entry in enumerate(iter_checkbox_entries(markdown)):
        prior_state = latest_states.get(entry.body)
        first_seen_index = prior_state[2] if prior_state is not None else index
        latest_states[entry.body] = (entry.section, entry.checked, first_seen_index)

    grouped: dict[str, list[str]] = {}
    unresolved_entries = sorted(
        (
            (first_seen_index, section, body)
            for body, (section, checked, first_seen_index) in latest_states.items()
            if not checked
        ),
        key=lambda item: item[0],
    )
    for _index, section, body in unresolved_entries:
        grouped.setdefault(section, []).append(body)

    return grouped


def scan_catchup_tasks_from_notes(notes: list[PriorNote]) -> CatchupScanResult:
    latest_states: dict[str, tuple[str, bool, int]] = {}
    entry_index = 0

    for note in notes:
        for entry in iter_checkbox_entries(note.path.read_text(encoding="utf-8")):
            prior_state = latest_states.get(entry.body)
            first_seen_index = prior_state[2] if prior_state is not None else entry_index
            latest_states[entry.body] = (entry.section, entry.checked, first_seen_index)
            entry_index += 1

    grouped: dict[str, list[str]] = {}
    unresolved_entries = sorted(
        (
            (first_seen_index, section, body)
            for body, (section, checked, first_seen_index) in latest_states.items()
            if not checked
        ),
        key=lambda item: item[0],
    )
    for _index, section, body in unresolved_entries:
        grouped.setdefault(section, []).append(body)

    return CatchupScanResult(
        scanned_files_count=len(notes),
        grouped_tasks=grouped,
        scanned_start=notes[0].note_date if notes else None,
        scanned_end=notes[-1].note_date if notes else None,
    )


def scan_catchup_tasks(
    notes_dir: Path, *, before: date, since: date | None = None
) -> CatchupScanResult:
    notes = list_dated_notes(notes_dir, before=before, since=since)
    return scan_catchup_tasks_from_notes(notes)


def render_carry_over(
    previous_date: date,
    grouped_tasks: dict[str, list[str]],
    *,
    bullet_marker: str,
) -> str:
    lines = [f"## Carry-over from {previous_date.isoformat()}", ""]
    for section, tasks in grouped_tasks.items():
        lines.append(f"### {section}")
        lines.append("")
        for task in tasks:
            lines.append(f"{bullet_marker} [ ] {task}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_catchup_block(grouped_tasks: dict[str, list[str]], *, bullet_marker: str) -> str:
    lines = [CATCHUP_START_MARKER, "## Catch-up", ""]
    for section, tasks in grouped_tasks.items():
        lines.append(f"### {section}")
        lines.append("")
        for task in tasks:
            lines.append(f"{bullet_marker} [ ] {task}")
        lines.append("")
    lines.append(CATCHUP_END_MARKER)
    return "\n".join(lines).rstrip() + "\n"


def replace_catchup_block(markdown: str, block: str | None) -> str:
    start_idx = markdown.find(CATCHUP_START_MARKER)
    end_idx = markdown.find(CATCHUP_END_MARKER)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        end_idx += len(CATCHUP_END_MARKER)
        prefix = markdown[:start_idx].rstrip()
        suffix = markdown[end_idx:].lstrip("\n")
        parts = [
            part for part in (prefix, block.rstrip() if block else "", suffix.rstrip()) if part
        ]
        if not parts:
            return ""
        return "\n\n".join(parts) + "\n"

    if block is None:
        return markdown if markdown.endswith("\n") or not markdown else f"{markdown}\n"

    base = markdown.rstrip()
    if not base:
        return block

    return f"{base}\n\n{block}"
