#!/usr/bin/env bash
set -euo pipefail

_psc_service_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${PY:-}" ]]; then
  PY=$(command -v python3) || { echo "python3 not found" >&2; exit 1; }
fi

stop_legacy_manager_timer() {
  local instance="${PSC_INSTANCE:-cortex}"
  if ! command -v systemctl >/dev/null 2>&1 || ! systemctl --user show-environment >/dev/null 2>&1; then
    return 0
  fi
  systemctl --user stop "${instance}-manager.timer" "${instance}-manager.service" >/dev/null 2>&1 || true
  systemctl --user disable "${instance}-manager.timer" >/dev/null 2>&1 || true
}

# #375：lock 路徑不得由 shell 自己硬寫一套解析規則——曾經固定回退到
# $HOME/.agents/control，與 Python daemon（control/constants.py →
# config/runtime.py 的完整 PSC_AGENTS_ROOT 解析鏈）各自為政；兩個 instance 的
# PSC_AGENTS_ROOT 不同時，wrapper 判斷的 lock 路徑就會跟 daemon 實際使用的分岔，
# 第二個 instance 啟動失敗時 wrapper 反而認養到另一個 instance 的 pid。改成呼叫
# 與 daemon 同源的 `cortex control lock-path` 契約；結果快取到
# _psc_manager_lock_path，避免 wait_for_manager_shutdown 的輪詢迴圈（最多 100 次、
# 每次間隔 0.05s）反覆 spawn python 拖慢 shutdown 偵測。
_psc_manager_lock_path=""

manager_lock_path() {
  if [[ -z "$_psc_manager_lock_path" ]]; then
    _psc_manager_lock_path="$("$PY" -m paulsha_cortex.cli control lock-path)"
  fi
  printf '%s\n' "$_psc_manager_lock_path"
}

is_live_manager_pid() {
  local pid="$1"
  if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
    return 1
  fi
  if [[ ! -r "/proc/$pid/cmdline" ]]; then
    return 1
  fi
  local cmdline_parts=()
  local idx
  mapfile -d '' -t cmdline_parts <"/proc/$pid/cmdline"
  for ((idx = 0; idx + 1 < ${#cmdline_parts[@]}; idx++)); do
    if [[ "${cmdline_parts[$idx]}" == "-m" && "${cmdline_parts[$((idx + 1))]}" == "paulsha_cortex.coordinator.manager_daemon" ]]; then
      return 0
    fi
  done
  return 1
}

read_live_manager_pid() {
  local lock_path
  lock_path="$(manager_lock_path)"
  if [[ ! -f "$lock_path" ]]; then
    return 0
  fi
  local owner_pid
  owner_pid="$(sed -n 's/.*"pid":[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$lock_path" | head -n 1)"
  if [[ -n "$owner_pid" ]] && is_live_manager_pid "$owner_pid"; then
    printf '%s\n' "$owner_pid"
  fi
}

read_manager_lock_owner_pid() {
  local lock_path
  lock_path="$(manager_lock_path)"
  if [[ ! -f "$lock_path" ]]; then
    return 0
  fi
  sed -n 's/.*"pid":[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$lock_path" | head -n 1
}

wait_for_manager_shutdown() {
  local pid="$1"
  local shutdown_checks=100
  local lock_owner_pid
  while (( shutdown_checks > 0 )); do
    lock_owner_pid="$(read_manager_lock_owner_pid)"
    if ! is_live_manager_pid "$pid" && [[ "$lock_owner_pid" != "$pid" ]]; then
      return 0
    fi
    shutdown_checks=$((shutdown_checks - 1))
    if (( shutdown_checks == 0 )); then
      return 0
    fi
    sleep 0.05
  done
}

start_manager_service() {
  if [[ "${PSC_MANAGER_DISABLED:-0}" == "1" ]]; then
    echo "manager service disabled (PSC_MANAGER_DISABLED=1)"
    return 0
  fi
  local instance="${PSC_INSTANCE:-cortex}"
  if ! command -v systemctl >/dev/null 2>&1 || ! systemctl --user show-environment >/dev/null 2>&1; then
    echo "manager service skipped: systemctl --user unavailable (WSL no user systemd?)" >&2
    return 0
  fi
  if [[ ! -f "$HOME/.config/systemd/user/${instance}-manager.timer" ]]; then
    echo "manager timer unit 未安裝，執行 installer ..."
    local installer="${PSC_MANAGER_INSTALLER:-}"
    if [[ -n "$installer" ]]; then
      if ! "$installer" "$instance"; then
        echo "manager units install failed (non-fatal)" >&2
        return 0
      fi
    else
      if ! "$PY" -m paulsha_cortex.cli install service --instance "$instance"; then
        echo "manager units install failed (non-fatal)" >&2
        return 0
      fi
    fi
  fi
  if systemctl --user start "${instance}-manager.timer"; then
    echo "manager timer started (${instance}-manager.timer)"
  else
    echo "manager timer start failed (non-fatal)" >&2
  fi
  return 0
}

start_manager_loop() {
  # F1（issue #2，Plan 3 真機實測到自停）：不得在此停 ${instance}-manager.*——
  # 本函式即 cortex-manager.service 的 ExecStart，stop_legacy_manager_timer 會停掉「自己」
  # （SIGTERM 自殺、Duration ~7ms）。cortex 為 timer+daemon 模型，舊 paulshaclaw 單元的
  # cutover 已由 operator shell（start.sh）在 enable 前負責，此處不再自停。
  if [[ "${PSC_MANAGER_DAEMON_DISABLED:-0}" == "1" ]]; then
    echo "manager loop disabled (PSC_MANAGER_DAEMON_DISABLED=1)"
    return 0
  fi
  mkdir -p "$HOME/.agents/log"
  local manager_log="$HOME/.agents/log/manager.log"
  # #375 評估後的取捨：PSC_MANAGER_SPECS_DIR（連同 PSC_COORDINATOR_ROOT／
  # PSC_SPECS_ROOT）目前仍刻意留在 operator 域，installer 不會幫它們 instance-
  # scope。這行的 `$HOME/.agents/specs` 預設同樣不會跟著 PSC_AGENTS_ROOT 走，
  # 是比 lock 路徑更直接的一個 isolation 破口（agents_root 已各自隔離的兩個
  # instance，沒設定 PSC_MANAGER_SPECS_DIR 時仍會共掃同一份 specs 目錄）。
  # 沒有跟著這次一併修的原因：coordinator_root 是 jobs.json／delivery-journal
  # 等大量既有呼叫點的共用 state root，改動面遠大於本次 CONTROL_ROOT／
  # PROJECT_CONFIG_ROOT 的範圍，需要獨立評估／測試，見
  # test_install_leaves_specs_and_coordinator_roots_as_operator_domain 的說明。
  (
    "$PY" -m paulsha_cortex.coordinator.manager_daemon \
      --specs-dir "${PSC_MANAGER_SPECS_DIR:-$HOME/.agents/specs}"
  ) 200>&- >>"$manager_log" 2>&1 &
  MANAGER_PID=$!
  MANAGER_PID_OWNED=1
  local manager_startup_checks=20
  local manager_state
  while (( manager_startup_checks > 0 )); do
    manager_state="$(ps -o stat= -p "$MANAGER_PID" 2>/dev/null | tr -d '[:space:]' || true)"
    if [[ -z "$manager_state" || "$manager_state" == *Z* ]]; then
      local existing_manager_pid
      existing_manager_pid="$(read_live_manager_pid)"
      wait "$MANAGER_PID" 2>/dev/null || true
      if [[ -n "$existing_manager_pid" && "$existing_manager_pid" != "$MANAGER_PID" ]]; then
        MANAGER_PID="$existing_manager_pid"
        MANAGER_PID_OWNED=0
        echo "manager pid=$MANAGER_PID (adopted existing)"
        return 0
      fi
      echo "manager daemon exited before startup" >&2
      exit 1
    fi
    manager_startup_checks=$((manager_startup_checks - 1))
    if (( manager_startup_checks == 0 )); then
      break
    fi
    sleep 0.05
  done
  echo "manager pid=$MANAGER_PID"
}

if [[ "${1:-}" == "--source-only" ]]; then
  return 0 2>/dev/null || exit 0
fi

unset _psc_service_dir

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  start_manager_loop
  if [[ -n "${MANAGER_PID:-}" ]]; then
    if [[ "${MANAGER_PID_OWNED:-1}" == "1" ]]; then
      wait "$MANAGER_PID"
    else
      wait_for_manager_shutdown "$MANAGER_PID"
    fi
  fi
fi
