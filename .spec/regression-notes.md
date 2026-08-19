# Regression notes

- Optional text inputs must not become required.
- Whitespace-only strings are valid.
- Missing and empty inputs must not leave separators.
- All-disabled output must be exact empty string.
- Runtime mode and mask must remain workflow-serialised.
- Every toggle and mode change must sync immediately.
- Live state overrides queued fallback only when a matching state exists.
- Runtime subclasses remain input-count driven.
- JavaScript discovers `text_N` inputs dynamically.
- String Output distinguishes empty string from never executed.
