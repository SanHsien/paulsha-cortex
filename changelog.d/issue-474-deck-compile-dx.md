# Issue #474 Deck compile DX

- Add fail-closed `cortex deck compile --policy-from <repo-relative-path>` for
  first-task policy candidates and `--slug` for stable CJK task slugs.
- Show combo card membership through `cortex deck list [combo]`, including
  band-triggered cards.
- Print the resolved output directory and every emitted filename; warn when
  `--repo` is omitted and the emitted authority remains `repo: null`.
- Let read-only `cortex ready` use the manager specs directory by default while
  keeping mutation commands explicit.
- Record the fork's per-point decision for upstream Issue #474 in the durable
  upstream ledger.
