# grunt quality evaluation

Blind pairwise judge: claude-fable-5. A = baseline (expensive model did the chore), B = grunt (cheap model did it). Arm order anonymized per pair.

| Task | Trial | Better artifact | Judge's reason |
|---|---|---|---|
| changelog | 1 | baseline | Y's commit message covers all changes while X's omits the math helpers, and X's changelog claims 16 dateutils functions but lists only 15 plus invents a 0.1.0 release version — Y is accurate, complete, and appropriately concise. |
| changelog | 2 | baseline | Y's commit message accurately labels the change as `feat` covering the new module and helpers, while X mislabels code additions as `docs:` and its changelog claims "16 date utility functions" but lists only 15. |
| changelog | 3 | baseline | Both are factually consistent, but Y correctly files the work under Unreleased (X leaves Unreleased empty and invents a dated release for an uncommitted change), its commit subject covers all three changes where X's omits the math helpers, and it conveys the same information with appropriate concision. |
| commit | 1 | baseline | X covers all three staged changes (dateutils, mathutils extension, docstrings) while Y silently omits the mathutils work, and X's extra length is a fair trade for that completeness within acceptable Conventional Commits form. |
| commit | 2 | tie | Both use correct Conventional Commits format, imperative mood, similar length, and describe the same changes with only trivial phrasing differences ("math helpers" vs "math functions with docstrings"), making neither clearly more accurate without seeing the diff. |
| commit | 3 | baseline | Both use valid Conventional Commits format, but X names the concrete additions (dateutils module, math helpers) while Y's "expand utility modules" is vague, making X the clearer message at comparable length. |
| log-filter | 1 | baseline | Both agree on facts and cover the task, but X adds the total ERROR count and presents the same information in a tighter table format, edging out Y on completeness and concision. |
| log-filter | 2 | tie | Both report identical, presumably correct counts (auth 10, payments 9, search 9) with valid example lines per service; X's table and Y's compact list are equally adequate markdown for the task. |
| log-filter | 3 | tie | Both report identical, correct counts (auth 10, search 9, payments 9) with the same valid example lines in clean markdown; X's total-line and table vs Y's per-service sections are equally adequate formats for the task. |
| pr-desc | 1 | baseline | X is more precise and factually careful (notes functions are stubs with no behavior changes, gives exact counts per module), while Y's prose overstates stub functions as "comprehensive date handling utilities" and pads with filler like "for clarity and maintainability." |
| pr-desc | 2 | baseline | X claims 16 dateutils stubs but lists only 15 (internal inconsistency), while Y is self-consistent, equally complete, and better structured with explicit Summary/Changes sections. |
| pr-desc | 3 | tie | Both hit the required format (title, summary, change bullets) with consistent facts — X adds useful convention context while Y adds fuller function-level detail, and neither pulls decisively ahead. |

**Grunt wins 0/12, ties 4/12, loses 8/12.**

## Objective checks (ground truth, no judge)

| Task | Arm | Trial | Check | Pass | Note |
|---|---|---|---|---|---|
| changelog | A | 1 | conventional subject | ✅ | feat: add dateutils module, new math helpers, and docstrings |
| changelog | A | 2 | conventional subject | ✅ | feat: add dateutils module, new math helpers, and docstrings |
| changelog | A | 3 | conventional subject | ✅ | feat: add dateutils module, new math helpers, and docstrings |
| commit | A | 1 | conventional subject | ✅ | feat: add dateutils module, extend mathutils, docstring all  |
| commit | A | 2 | conventional subject | ✅ | feat: add dateutils module, new math helpers, and docstrings |
| commit | A | 3 | conventional subject | ✅ | feat: add dateutils module, math helpers, and docstrings |
| log-filter | A | 1 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | A | 2 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | A | 3 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| changelog | B | 1 | conventional subject | ✅ | feat: add dateutils module and docstrings |
| changelog | B | 2 | conventional subject | ✅ | docs: add changelog and module docstrings |
| changelog | B | 3 | conventional subject | ✅ | feat: add dateutils module and docstrings |
| commit | B | 1 | conventional subject | ✅ | feat: add dateutils module and docstrings |
| commit | B | 2 | conventional subject | ✅ | feat: add dateutils module and math functions with docstring |
| commit | B | 3 | conventional subject | ✅ | feat: add docstrings and expand utility modules |
| log-filter | B | 1 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | B | 2 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | B | 3 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |

Objective pass rate: baseline 9/9, grunt 9/9.
