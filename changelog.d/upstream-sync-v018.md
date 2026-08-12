# Upstream v0.1.8 sync

- Adopt upstream PRs #467, #468, and #470–#472 through `dc8a968`, including
  explicit workflow/slice repo attribution, patchmud profile drift repairs,
  and the deterministic Stage 9 readiness regression.
- Preserve the fork's Windows patchmud shebang adapter and native monitor
  transport while resolving overlapping files; keep the upstream POSIX-mode
  slow-chmod regression skipped where Windows ACLs have no equivalent mode bits.
- Reserve durable profile run directories with atomic `mkdir` collision handling
  so concurrent commands sharing one timestamp cannot select the same path.
- Add `cortex deck compile --repo owner/repo` so an explicit work-item repo is
  written into emitted slice specs; omission remains `repo: null` and no path
  or Git-remote inference is introduced.
- Advance `docs/UPSTREAM.md` to `dc8a968` with per-PR and per-issue decisions.
