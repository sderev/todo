# Changelog fragments

Use scriv fragments to record user-facing changes before release.

## Workflow
1. Run `uv run --extra dev scriv create`.
2. Edit the new file under `changelog.d/` using the template prompts.
3. Keep each change under the correct heading (Added, Changed, Deprecated, Removed, Fixed, Security).
4. Use short, past-tense bullet points.
5. Commit the fragment with the related code change.
6. Do not collect fragments manually; release automation should run `scriv collect`.

## Tips
* One fragment per logical change keeps history clear.
* Preview fragments without modifying files: `uv run --extra dev scriv print` (returns status 2 if no fragments exist).
