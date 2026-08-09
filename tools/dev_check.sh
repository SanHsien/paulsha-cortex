#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
python_version="$(tr -d '[:space:]' < "$repo_root/.python-version")"
repo_key="$(printf '%s' "$repo_root" | sha256sum | cut -c1-12)"
venv_root="${XDG_CACHE_HOME:-$HOME/.cache}/paulsha-cortex/venvs/${repo_key}-py${python_version}"
quick=0

if [[ "${1:-}" == "--quick" ]]; then
  quick=1
elif [[ -n "${1:-}" ]]; then
  printf '未知參數：%s\n' "$1" >&2
  exit 2
fi

if [[ ! -x "$venv_root/bin/python" ]]; then
  "$repo_root/tools/bootstrap_dev.sh"
fi

cd "$repo_root"
git diff --check 2>/dev/null
git diff --cached --check 2>/dev/null

crlf_shell_files="$(git grep -Il $'\r' -- '*.sh' || true)"
if [[ -n "$crlf_shell_files" ]]; then
  printf 'Shell scripts 必須使用 LF：\n%s\n' "$crlf_shell_files" >&2
  exit 1
fi

"$venv_root/bin/python" -m compileall -q paulsha_cortex

if (( quick )); then
  "$venv_root/bin/python" -m pytest -q \
    tests/test_cli_entry.py \
    tests/test_development_environment.py \
    tests/test_release_pipeline_workflows.py \
    tests/test_zero_dependency_runtime.py
  exit 0
fi

"$venv_root/bin/python" -m pytest tests/ -q
dist_root="$(mktemp -d)"
trap 'rm -rf "$dist_root"' EXIT
"$venv_root/bin/python" -m build --outdir "$dist_root"
