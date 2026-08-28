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


def test_powershell_wrappers_are_native_windows_first() -> None:
    bootstrap = (ROOT / "tools" / "bootstrap_dev.ps1").read_text(encoding="utf-8")
    dev_check = (ROOT / "tools" / "dev_check.ps1").read_text(encoding="utf-8")

    assert "wsl.exe" not in bootstrap
    assert "wsl.exe" not in dev_check
    assert '".venv"' in bootstrap
    assert '"Scripts\\python.exe"' in bootstrap
    assert 'uv.exe python find $desiredPython' in bootstrap
    assert '(3, 10) <= sys.version_info < (3, 14)' in bootstrap
    assert 'foreach ($version in @("3.13", "3.12", "3.11", "3.10"))' in bootstrap
    assert '$candidates += ,@($launcher, "-$version")' in bootstrap
    assert "既有 .venv 使用不支援的 Python" in bootstrap
    assert bootstrap.count("(3, 10) <= sys.version_info < (3, 14)") == 2
    assert bootstrap.index('$venvPython = Join-Path $venvRoot') < bootstrap.index("$candidates = @()")
    assert '} else {\n    $candidates = @()' in bootstrap
    assert ".venv\\Scripts\\python.exe" in dev_check
    assert "-m pytest tests -q" in dev_check
    assert "-m build --outdir" in dev_check
    assert "-m twine check --strict" in dev_check


def test_dev_extra_and_python_version_are_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[project.optional-dependencies]" in pyproject
    assert '"pytest>=' in pyproject
    assert '"build>=' in pyproject
    assert '"twine>=' in pyproject
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
