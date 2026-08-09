from __future__ import annotations

from pathlib import Path
import os
import shutil

import pytest


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep tests hermetic against operator shell/runtime bootstrap variables.

    Clearing PSC_* alone is not enough: paulsha_cortex.config.runtime falls
    back to the *installed* instance under the real ``$HOME`` (bootstrap env
    file, then ``Path.home() / ".agents"``) whenever a root is unset. Without
    an explicit redirect, any test that forgets to isolate its own coordinator
    root (JobRegistry(), IdentityRegistry(), paths.coordinator_root(), ...)
    silently reads (and, on schema migration, could even write) the operator's
    real production state — see #303. Point the whole PSC_AGENTS_ROOT family
    (coordinator/control/specs/monitor/project-config/run root all derive
    from it, see config/runtime.py RUNTIME_ROOT_DEFAULTS) plus PSC_CONFIG_ROOT
    at an empty per-test directory by default; tests that need specific fixture
    data still monkeypatch these explicitly afterwards, which overrides this.
    """
    for name in tuple(os.environ):
        if name.startswith("PSC_") or name == "PAULSHACLAW_CONFIG":
            monkeypatch.delenv(name, raising=False)
    unset_root = tmp_path / "unset-psc-root-guard"
    monkeypatch.setenv("PSC_AGENTS_ROOT", str(unset_root / "agents"))
    monkeypatch.setenv("PSC_CONFIG_ROOT", str(unset_root / "config"))


@pytest.fixture(autouse=True)
def _skip_symlink_tests_without_windows_privilege(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip only when the host cannot create the symlink required by a test.

    Windows requires Developer Mode or SeCreateSymbolicLinkPrivilege.  Linux CI
    still exercises every symlink security assertion; native Windows reports a
    precise skip instead of failing before product code is reached.
    """
    if os.name != "nt":
        return
    original = os.symlink

    def guarded_symlink(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                pytest.skip("Windows symlink privilege is unavailable")
            raise

    monkeypatch.setattr(os, "symlink", guarded_symlink)


@pytest.fixture(autouse=True)
def _prefer_local_openspec(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    wrapper = repo_root / "scripts" / "openspec"
    if not wrapper.exists():
        return

    real_openspec = shutil.which("openspec")
    if real_openspec:
        monkeypatch.setenv("PAULSHA_REAL_OPENSPEC", real_openspec)

    original_path = os.environ.get("PATH", "")
    wrapper_parent = str(wrapper.parent.resolve())
    if wrapper_parent not in original_path.split(os.pathsep):
        monkeypatch.setenv("PATH", f"{wrapper_parent}{os.pathsep}{original_path}")
