#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
python_version="$(tr -d '[:space:]' < "$repo_root/.python-version")"

linuxbrew_home="$(getent passwd linuxbrew | cut -d: -f6 2>/dev/null || true)"
for bin_dir in "$HOME/.local/bin" "${linuxbrew_home:+$linuxbrew_home/.linuxbrew/bin}"; do
  [[ -n "$bin_dir" ]] || continue
  if [[ -d "$bin_dir" ]]; then
    PATH="$bin_dir:$PATH"
  fi
done
export PATH

if ! command -v uv >/dev/null 2>&1; then
  printf '缺少 uv。請先在 WSL 安裝：https://docs.astral.sh/uv/getting-started/installation/\n' >&2
  exit 1
fi

cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/paulsha-cortex"
repo_key="$(printf '%s' "$repo_root" | sha256sum | cut -c1-12)"
venv_root="$cache_root/venvs/${repo_key}-py${python_version}"

mkdir -p "$(dirname "$venv_root")"
if [[ ! -x "$venv_root/bin/python" ]]; then
  uv venv --python "$python_version" "$venv_root"
fi

uv pip install --python "$venv_root/bin/python" -e "${repo_root}[dev]"

missing_runtime=()
for command_name in bwrap socat; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    missing_runtime+=("$command_name")
  fi
done

printf '開發環境完成：%s\n' "$venv_root"
if (( ${#missing_runtime[@]} > 0 )); then
  printf '核心開發可用；完整 foreign-review runtime 尚缺：%s\n' "${missing_runtime[*]}" >&2
  printf 'Ubuntu/WSL 可執行：sudo apt-get install bubblewrap socat\n' >&2
fi
