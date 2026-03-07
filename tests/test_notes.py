from datetime import date
from pathlib import Path

from todocli.config import Config
from todocli.notes import (
    collect_unchecked_tasks,
    find_latest_note_before,
    note_path_for_date,
    parse_note_date,
    render_carry_over,
)


def test_collect_unchecked_tasks_groups_by_h2_heading() -> None:
    markdown = """# 2026-03-06

## Campus network
- [ ] Check switch room B
- [X] Done item

## Storage
- [ ] Validate snapshots
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {
        "Campus network": ["Check switch room B"],
        "Storage": ["Validate snapshots"],
    }


def test_collect_unchecked_tasks_handles_no_h2_with_general_bucket() -> None:
    markdown = """# 2026-03-06
- [ ] Follow up with facilities
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {"General": ["Follow up with facilities"]}


def test_collect_unchecked_tasks_deduplicates_items_per_section() -> None:
    markdown = """# 2026-03-06

## Ops
- [ ] Update package index
- [ ] Update package index
* [ ] Restart monitoring
- [x] Done item
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {
        "Ops": ["Update package index", "Restart monitoring"],
    }


def test_collect_unchecked_tasks_preserves_generated_carry_over_sections() -> None:
    markdown = """# 2026-03-09

## Carry-over from 2026-03-06

### Campus network
- [ ] Check switch room B

### Storage
- [ ] Validate snapshots
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {
        "Campus network": ["Check switch room B"],
        "Storage": ["Validate snapshots"],
    }


def test_find_latest_note_before_ignores_invalid_and_future_files(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    (notes_dir / "2026" / "03").mkdir(parents=True, exist_ok=True)

    (notes_dir / "2026" / "03" / "2026-03-05.md").write_text("# a\n", encoding="utf-8")
    latest = notes_dir / "2026" / "03" / "2026-03-07.md"
    latest.write_text("# b\n", encoding="utf-8")
    (notes_dir / "2026" / "03" / "2026-03-10.md").write_text("# c\n", encoding="utf-8")
    (notes_dir / "2026" / "03" / "notes.md").write_text("# not a date\n", encoding="utf-8")

    prior = find_latest_note_before(notes_dir, before=date(2026, 3, 9))

    assert prior is not None
    assert prior.note_date == date(2026, 3, 7)
    assert prior.path == latest


def test_note_path_for_date_supports_flat_layout(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="flat", carry_over_mode="auto")

    path = note_path_for_date(config, date(2026, 3, 9))

    assert path == notes_dir / "2026-03-09.md"


def test_parse_note_date_returns_none_for_non_date_filename(tmp_path: Path) -> None:
    assert parse_note_date(tmp_path / "notes.md") is None


def test_render_carry_over_keeps_section_context() -> None:
    rendered = render_carry_over(
        date(2026, 3, 6),
        {
            "Campus network": ["Check switch room B"],
            "Storage": ["Validate snapshots"],
        },
    )

    assert "## Carry-over from 2026-03-06" in rendered
    assert "### Campus network" in rendered
    assert "- [ ] Check switch room B" in rendered
    assert "### Storage" in rendered
