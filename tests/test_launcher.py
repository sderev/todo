import subprocess
from pathlib import Path


def test_repo_launcher_uses_project_environment(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [str(repo_root / "todo"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: todo [OPTIONS] COMMAND [ARGS]..." in result.stdout


def test_repo_launcher_supports_version_option(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [str(repo_root / "todo"), "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("todo, version ")
