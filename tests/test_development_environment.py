from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_fork_development_environment_files_exist() -> None:
    expected = {
        ".editorconfig",
        ".gitattributes",
        ".github/dependabot.yml",
        ".github/pull_request_template.md",
        ".github/workflows/codeql.yml",
        ".python-version",
        "CODE_OF_CONDUCT.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/DECISIONS.md",
        "docs/DEVELOPMENT.md",
        "docs/FORK.md",
        "tools/bootstrap_dev.ps1",
        "tools/bootstrap_dev.sh",
        "tools/dev_check.ps1",
        "tools/dev_check.sh",
    }

    missing = sorted(path for path in expected if not (ROOT / path).is_file())
    assert missing == []


def test_checkout_contract_keeps_shell_scripts_lf() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "* text=auto eol=lf" in attributes

    for script in sorted((ROOT / "tools").glob("*.sh")):
        content = script.read_bytes()
        assert content.startswith(b"#!/usr/bin/env bash\n")
        assert b"\r\n" not in content


def test_powershell_wrappers_resolve_windows_paths_with_wsl_cd() -> None:
    for script_name in ("bootstrap_dev.ps1", "dev_check.ps1"):
        content = (ROOT / "tools" / script_name).read_text(encoding="utf-8")
        assert "--cd $repoRoot -- pwd" in content
        assert "wslpath" not in content
        assert "$wslExitCode = $LASTEXITCODE" in content
        assert "$wslRepoRoot = ($wslRepoOutput | Out-String).Trim()" in content


def test_dev_extra_and_python_version_are_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.optional-dependencies]" in pyproject
    assert '"pytest>=' in pyproject
    assert '"build>=' in pyproject
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.13"


def test_dev_check_covers_staged_changes_and_versioned_venv() -> None:
    bootstrap = (ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")
    dev_check = (ROOT / "tools" / "dev_check.sh").read_text(encoding="utf-8")

    assert 'venvs/${repo_key}-py${python_version}' in bootstrap
    assert 'venvs/${repo_key}-py${python_version}' in dev_check
    assert "git diff --check" in dev_check
    assert "git diff --cached --check" in dev_check


def test_bootstrap_has_no_personal_absolute_linuxbrew_path() -> None:
    bootstrap = (ROOT / "tools" / "bootstrap_dev.sh").read_text(encoding="utf-8")

    assert "/home/linuxbrew" not in bootstrap
    assert "getent passwd linuxbrew" in bootstrap


def test_readme_links_fork_development_documents() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for path in ("docs/DEVELOPMENT.md", "docs/FORK.md", "docs/DECISIONS.md"):
        assert f"]({path})" in readme
