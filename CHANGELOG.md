# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

<!-- scriv-insert-here -->

<a id='changelog-0.2.1'></a>
## 0.2.1 - 2026-03-18

Fixed
-----
* Made `todo review` default to the weekly review command instead of requiring `todo review week`.

<a id='changelog-0.2.0'></a>
## 0.2.0 - 2026-03-18

Added
-----
* Add `todo review week` to build a weekly markdown report from dated notes.

<a id='changelog-0.1.4'></a>
## 0.1.4 - 2026-03-10

Added
-----
* Add `bullet_marker` config setting (and `--bullet-marker` CLI option) to choose between `*` and `-` as the bullet character for generated checkbox lists. Applies to `today` carry-over, `catchup` output, and `--dry-run` preview.

<a id='changelog-0.1.3'></a>
## 0.1.3 - 2026-03-07

Added
-----
* Add `--version` to print the installed `todo` CLI version.

Fixed
-----
* Align package metadata version with release tags so `todo --version` reports the current release version.
