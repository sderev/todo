from datetime import date
from pathlib import Path

from todocli.config import Config
from todocli.notes import (
    collect_unchecked_tasks,
    compute_weekly_review,
    find_latest_note_before,
    iso_week_range,
    iso_week_range_from_week,
    list_dated_notes,
    note_path_for_date,
    parse_note_date,
    render_carry_over,
    render_catchup_block,
    replace_catchup_block,
    scan_catchup_tasks,
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


def test_collect_unchecked_tasks_accepts_bare_checkbox_lines() -> None:
    markdown = """# 2026-03-06

## Campus network
[ ] Check switch room B
[x] Done item

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


def test_collect_unchecked_tasks_uses_latest_state_within_same_note() -> None:
    markdown = """# 2026-03-06

## Ops
- [ ] Update package index
- [x] Update package index
- [ ] Reply to NOC
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {"Ops": ["Reply to NOC"]}


def test_collect_unchecked_tasks_uses_latest_state_when_task_moves_sections() -> None:
    markdown = """# 2026-03-06

## Ops
- [ ] Update package index

## Tickets
- [x] Update package index
"""

    grouped = collect_unchecked_tasks(markdown)

    assert grouped == {}


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


def test_find_latest_note_before_ignores_invalid_and_future_files(
    tmp_path: Path,
) -> None:
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
        bullet_marker="*",
    )

    assert "## Carry-over from 2026-03-06" in rendered
    assert "### Campus network" in rendered
    assert "* [ ] Check switch room B" in rendered
    assert "### Storage" in rendered


def test_list_dated_notes_respects_since_inclusive(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    (notes_dir / "2026" / "03").mkdir(parents=True, exist_ok=True)
    for day in (4, 5, 6):
        (notes_dir / "2026" / "03" / f"2026-03-0{day}.md").write_text("# note\n", encoding="utf-8")

    notes = list_dated_notes(notes_dir, before=date(2026, 3, 7), since=date(2026, 3, 5))

    assert [note.note_date for note in notes] == [date(2026, 3, 5), date(2026, 3, 6)]


def test_scan_catchup_tasks_keeps_latest_checkbox_state_per_task_key(
    tmp_path: Path,
) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    march_4 = note_path_for_date(config, date(2026, 3, 4))
    march_4.parent.mkdir(parents=True, exist_ok=True)
    march_4.write_text(
        """# 2026-03-04

## Ops
- [ ] Update package index

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

## Ops
- [x] Update package index

## Tickets
- [ ] Reply to NOC
""",
        encoding="utf-8",
    )

    march_6 = note_path_for_date(config, date(2026, 3, 6))
    march_6.parent.mkdir(parents=True, exist_ok=True)
    march_6.write_text(
        """# 2026-03-06

## Carry-over from 2026-03-05

### Tickets
- [x] Reply to NOC

### Storage
- [ ] Validate snapshots
""",
        encoding="utf-8",
    )

    result = scan_catchup_tasks(notes_dir, before=date(2026, 3, 7))

    assert result.scanned_files_count == 3
    assert result.scanned_start == date(2026, 3, 4)
    assert result.scanned_end == date(2026, 3, 6)
    assert result.grouped_tasks == {"Storage": ["Validate snapshots"]}


def test_scan_catchup_tasks_preserves_latest_state_across_historical_managed_catchup_blocks(
    tmp_path: Path,
) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    march_4 = note_path_for_date(config, date(2026, 3, 4))
    march_4.parent.mkdir(parents=True, exist_ok=True)
    march_4.write_text(
        """# 2026-03-04

## Ops
- [ ] Update package index
""",
        encoding="utf-8",
    )

    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

<!-- todo catchup start -->
## Catch-up

### Ops
- [ ] Update package index
<!-- todo catchup end -->
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

    result = scan_catchup_tasks(notes_dir, before=date(2026, 3, 7))

    assert result.scanned_files_count == 3
    assert result.grouped_tasks == {}


def test_scan_catchup_tasks_uses_latest_state_when_task_moves_sections(
    tmp_path: Path,
) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    march_4 = note_path_for_date(config, date(2026, 3, 4))
    march_4.parent.mkdir(parents=True, exist_ok=True)
    march_4.write_text(
        """# 2026-03-04

## Ops
- [ ] Update package index
""",
        encoding="utf-8",
    )

    march_5 = note_path_for_date(config, date(2026, 3, 5))
    march_5.parent.mkdir(parents=True, exist_ok=True)
    march_5.write_text(
        """# 2026-03-05

## Tickets
- [x] Update package index
""",
        encoding="utf-8",
    )

    result = scan_catchup_tasks(notes_dir, before=date(2026, 3, 7))

    assert result.scanned_files_count == 2
    assert result.grouped_tasks == {}


def test_replace_catchup_block_replaces_existing_managed_section() -> None:
    original = """# 2026-03-09

Manual note

<!-- todo catchup start -->
## Catch-up

### Ops
- [ ] Old task
<!-- todo catchup end -->

## Later
still here
"""

    updated = replace_catchup_block(
        original,
        render_catchup_block(
            {"Ops": ["New task"], "Tickets": ["Reply to NOC"]},
            bullet_marker="*",
        ),
    )

    assert updated.count("<!-- todo catchup start -->") == 1
    assert "Old task" not in updated
    assert "* [ ] New task" in updated
    assert "## Later\nstill here\n" in updated


# --- Weekly review ---


# ISO week range calculation


def test_iso_week_range_midweek_anchor() -> None:
    # 2026-03-11 is a Wednesday in ISO week 2026-W11
    week = iso_week_range(date(2026, 3, 11))

    assert week.monday == date(2026, 3, 9)
    assert week.sunday == date(2026, 3, 15)
    assert week.cutoff == date(2026, 3, 11)


def test_iso_week_range_monday_anchor() -> None:
    week = iso_week_range(date(2026, 3, 9))

    assert week.monday == date(2026, 3, 9)
    assert week.sunday == date(2026, 3, 15)
    assert week.cutoff == date(2026, 3, 9)


def test_iso_week_range_sunday_anchor() -> None:
    week = iso_week_range(date(2026, 3, 15))

    assert week.monday == date(2026, 3, 9)
    assert week.sunday == date(2026, 3, 15)
    assert week.cutoff == date(2026, 3, 15)


def test_iso_week_range_from_week_number() -> None:
    week = iso_week_range_from_week(2026, 11)

    assert week.monday == date(2026, 3, 9)
    assert week.sunday == date(2026, 3, 15)
    assert week.cutoff == date(2026, 3, 15)


# Completed vs open classification


def test_weekly_review_classifies_done_and_open(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    # Monday: open two tasks
    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [ ] Deploy v2\n- [ ] Fix alerts\n",
        encoding="utf-8",
    )

    # Wednesday: complete one
    wed = note_path_for_date(config, date(2026, 3, 11))
    wed.parent.mkdir(parents=True, exist_ok=True)
    wed.write_text(
        "# 2026-03-11\n\n## Ops\n- [x] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {"Ops": ["Deploy v2"]}
    assert result.open == {"Ops": ["Fix alerts"]}
    assert result.scanned_files_count == 2


# Current partial week cutoff


def test_weekly_review_partial_week_excludes_future_notes(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    # Monday: open task
    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [ ] Deploy v2\n",
        encoding="utf-8",
    )

    # Friday: complete it
    fri = note_path_for_date(config, date(2026, 3, 13))
    fri.parent.mkdir(parents=True, exist_ok=True)
    fri.write_text(
        "# 2026-03-13\n\n## Ops\n- [x] Deploy v2\n",
        encoding="utf-8",
    )

    # Anchor is Wednesday → cutoff before Friday → should not see Friday's note
    week = iso_week_range(date(2026, 3, 11))
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {}
    assert result.open == {"Ops": ["Deploy v2"]}
    assert result.scanned_files_count == 1  # only Monday's note


# Tasks completed during week but reopened by cutoff


def test_weekly_review_completed_then_reopened_not_in_done(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    # Monday: complete a task
    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [x] Deploy v2\n",
        encoding="utf-8",
    )

    # Wednesday: reopen the same task
    wed = note_path_for_date(config, date(2026, 3, 11))
    wed.parent.mkdir(parents=True, exist_ok=True)
    wed.write_text(
        "# 2026-03-11\n\n## Ops\n- [ ] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {}
    assert result.open == {"Ops": ["Deploy v2"]}


# Tasks completed before the week and unchanged


def test_weekly_review_pre_week_completed_excluded_from_done(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    # Previous week: complete a task
    prev = note_path_for_date(config, date(2026, 3, 5))
    prev.parent.mkdir(parents=True, exist_ok=True)
    prev.write_text(
        "# 2026-03-05\n\n## Ops\n- [x] Deploy v1\n",
        encoding="utf-8",
    )

    # This week: a different task
    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [ ] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert "Deploy v1" not in result.done.get("Ops", [])
    assert result.open == {"Ops": ["Deploy v2"]}


# Empty input / no dated notes


def test_weekly_review_empty_notes_dir(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {}
    assert result.open == {}
    assert result.scanned_files_count == 0


def test_weekly_review_nonexistent_notes_dir(tmp_path: Path) -> None:
    notes_dir = tmp_path / "does_not_exist"

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {}
    assert result.open == {}
    assert result.scanned_files_count == 0


# Duplicate text behavior


def test_weekly_review_duplicate_task_body_uses_latest_state(tmp_path: Path) -> None:
    """Same body appearing in multiple notes: latest state wins."""
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    # Monday: open
    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [ ] Deploy v2\n- [ ] Deploy v2\n",
        encoding="utf-8",
    )

    # Tuesday: complete
    tue = note_path_for_date(config, date(2026, 3, 10))
    tue.parent.mkdir(parents=True, exist_ok=True)
    tue.write_text(
        "# 2026-03-10\n\n## Ops\n- [x] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    # Task appears only once despite duplicates in source
    assert result.done == {"Ops": ["Deploy v2"]}
    assert result.open == {}


# Additional edge cases


def test_weekly_review_task_section_uses_latest_note_section(tmp_path: Path) -> None:
    """When a task moves sections across notes, the latest section wins."""
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n## Ops\n- [ ] Deploy v2\n",
        encoding="utf-8",
    )

    wed = note_path_for_date(config, date(2026, 3, 11))
    wed.parent.mkdir(parents=True, exist_ok=True)
    wed.write_text(
        "# 2026-03-11\n\n## Tickets\n- [x] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    # Task classified under its latest section
    assert result.done == {"Tickets": ["Deploy v2"]}
    assert "Ops" not in result.done


def test_weekly_review_includes_pre_week_open_tasks(tmp_path: Path) -> None:
    """Tasks opened before the week that remain unchecked appear in open."""
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    prev = note_path_for_date(config, date(2026, 3, 5))
    prev.parent.mkdir(parents=True, exist_ok=True)
    prev.write_text(
        "# 2026-03-05\n\n## Ops\n- [ ] Old task\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.open == {"Ops": ["Old task"]}
    assert result.done == {}


def test_weekly_review_carry_over_sections_parsed(tmp_path: Path) -> None:
    """Tasks inside carry-over sections are tracked correctly."""
    notes_dir = tmp_path / "notes"
    config = Config(notes_dir=notes_dir, layout="year_month", carry_over_mode="auto")

    mon = note_path_for_date(config, date(2026, 3, 9))
    mon.parent.mkdir(parents=True, exist_ok=True)
    mon.write_text(
        "# 2026-03-09\n\n"
        "## Carry-over from 2026-03-06\n\n"
        "### Storage\n"
        "- [ ] Validate snapshots\n\n"
        "## Ops\n"
        "- [x] Deploy v2\n",
        encoding="utf-8",
    )

    week = iso_week_range_from_week(2026, 11)
    result = compute_weekly_review(notes_dir, week)

    assert result.done == {"Ops": ["Deploy v2"]}
    assert result.open == {"Storage": ["Validate snapshots"]}
