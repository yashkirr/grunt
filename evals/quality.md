# grunt quality evaluation

Blind pairwise judge: claude-fable-5. A = baseline (expensive model did the chore), B = grunt (cheap model did it). Arm order anonymized per pair.

| Task | Trial | Better artifact | Judge's reason |
|---|---|---|---|
| changelog | 1 | baseline | X is internally consistent and its commit message covers all changes (dateutils, math helpers, docstrings), while Y claims "16 date utility functions" but lists only 15 and its commit message omits the docstrings/README additions; X's concision is appropriate, and Y's bracketed [Unreleased] convention edge doesn't offset the factual miscount. |
| changelog | 2 | baseline | Both cover the task, but Y is tighter and cleaner while X pads with a redundant "Changed" entry duplicating its docstrings bullet and miscategorizes "Updated README" under Added. |
| changelog | 3 | baseline | X is factually correct (the fixture stages exactly 15 dateutils functions — Y says 16) and uses the standard "Unreleased" Keep-a-Changelog heading, while both are otherwise complete and clear. |
| commit | 1 | baseline | Both are well-formed Conventional Commits subjects of acceptable length, but X captures the mathutils extension that Y omits, making it more complete while staying concise. |
| commit | 2 | baseline | Assuming both describe the same staged diff, Y covers all changes (dateutils, math helpers, docstrings) while X omits two of three, and completeness of what actually got committed outweighs Y's slightly long subject line. |
| commit | 3 | tie | Both are well-formed, concise Conventional Commits subjects; without the staged diff there is no ground truth to confirm whether X's extra "math helpers" claim is accurate coverage or fabrication, so neither can be ranked above the other. |
| log-filter | 1 | tie | Identical facts (28 total; auth 10, payments 9, search 9, same example lines) and both fully satisfy the task — X's separate code blocks vs Y's tighter inline table is a style wash. |
| log-filter | 2 | tie | Both attempts report identical, verified-correct counts and example lines; X is slightly more concise with a helpful total while Y is slightly more readable, so both are fully adequate. |
| log-filter | 3 | tie | Both report identical, mutually consistent counts (auth 10, search 9, payments 9) with the same valid example lines in clean markdown, and Y's extra total (28) doesn't meaningfully outweigh X's equally adequate format. |
| pr-desc | 1 | baseline | Both are factually consistent and complete, but X's per-file breakdown with exact counts, conventional Summary/Changes structure, and the useful "no behavior changes" note beat Y's more generic, slightly padded prose. |
| pr-desc | 2 | baseline | Both are accurate, but Y is more precise and useful — exact file paths, full function-name list, and the stub-convention note — with proper Summary/Changes structure, while X pads with vaguer marketing-style prose ("establishes a foundation") and omits file paths. |
| pr-desc | 3 | baseline | Y is fully accurate and complete (correct 15 date stubs, correctly names the 5 new mathutils helpers), while X miscounts both modules (16 date stubs, "14" math functions) and entirely omits the 5 new math functions added in the staged diff. |

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
| changelog | B | 1 | conventional subject | ✅ | feat: add dateutils and expand math functions |
| changelog | B | 2 | conventional subject | ❌ | feat(modules): add dateutils module and comprehensive functi |
| changelog | B | 3 | conventional subject | ✅ | feat: add dateutils and expand utilities |
| commit | B | 1 | conventional subject | ✅ | feat: add dateutils module and docstrings to utility functio |
| commit | B | 2 | conventional subject | ✅ | feat: add dateutils module |
| commit | B | 3 | conventional subject | ✅ | feat: add dateutils module and docstrings for utility functi |
| log-filter | B | 1 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | B | 2 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |
| log-filter | B | 3 | correct counts {'auth': 10, 'payments': 9, 'search': 9} | ✅ |  |

Objective pass rate: baseline 9/9, grunt 8/9.
