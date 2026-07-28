---
status: done
work_item: dedupe-legacy-config-warnings-delivery
---

# Tasks

- [x] [RED] Add isolated warning-state fixture for per-process warning dedupe tests
- [x] [RED] Add legacy file fallback once-only regression test
- [x] [RED] Add legacy env fallback once-only regression test
- [x] [RED] Add new config no-warning regression test
- [x] [RED] Run failing regression test suite and commit
- [x] [GREEN] Implement one-shot warning dedupe helper in production code
- [x] [GREEN] Route both legacy paths through helper with distinct keys
- [x] [GREEN] Verify focused tests pass and commit implementation
- [x] [DOC] Update changelog and docs, then complete governance checks
- [x] [REPAIR] Preserve legacy warning attribution by keeping `stacklevel=2`
- [x] [REPAIR] Add regression test to lock warning caller attribution
