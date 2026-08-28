# Upstream v0.1.7 sync

- Adopt upstream PRs #457–#463 through `cf791a2`, including model envelope
  defaults, mapping, patchmud profiling, roster metadata, inspection, and the
  ship-phase `provider:executor` gate.
- Preserve the fork's Windows runtime, stdin hardening, and platform-specific
  documentation while resolving overlapping files.
- Fix upstream issue #464's socket-permission test race by waiting for the
  server readiness authority published after bind, chmod, and listen.
- Discover Python shebang patchmud entry points on the Windows PATH and launch
  them through the active interpreter while leaving native shims unchanged.
- Advance `docs/UPSTREAM.md` to `cf791a2` with per-PR and per-issue decisions.
