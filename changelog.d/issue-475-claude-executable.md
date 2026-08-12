# Issue #475 Claude executable provenance

- Add instance/process `PSC_CLAUDE_EXECUTABLE` binding for Claude
  Code-compatible launchers without expanding interactive shell aliases.
- Require an absolute, regular, non-symlink executable and fail closed instead
  of falling back to a different `claude` on PATH when an override is invalid.
- Report the resolved path through bootstrap and doctor, persist it as each
  launched Claude job's `executable_path`, validate installed runtime envs, and
  bind the dispatch auth probe plus TTL cache identity to the same resolved
  override-or-PATH path.
- Record the fork decision and future comparison boundary in the upstream
  ledger without making repo model overlays an arbitrary execution authority.
