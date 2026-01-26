# DEPRECATED

**Date:** 2026-01-26
**Replacement:** `sentinel-doc-sync`
**Reason:** ByteRover integration merged into `sentinel-doc-sync`. Single skill now handles:
- AGENTS.md synchronization
- docs/plans/ updates
- lessons-learned.md entries
- ByteRover curation (`brv curate`)

The prompt-based memory sync is obsolete. Use `sentinel-doc-sync` for all memory operations.

## Migration

Old workflow:
```
memory-sync → brv curate
```

New workflow:
```
sentinel-doc-sync (includes brv curate as Step 4)
```
