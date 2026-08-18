# Runtime Toggle String Join specification

## Purpose

Preserve large pre-queued job sequences while allowing only the prompt inclusion
mask and selection mode to change after queue submission.

## Queue-time data

- Upstream node graph and settings
- Runtime-generated upstream STRING operations
- Separator
- Saved fallback mode
- Saved fallback enabled mask
- Saved fallback selected index
- Persistent state key

## Execution-time live data

- Mode
- Enabled mask
- Selected index
- Revision

## State flow

1. UI action changes hidden saved widget values.
2. UI marks the workflow changed.
3. UI POSTs the same state to the server route.
4. Server validates and stores the state under `state_key`.
5. `IS_CHANGED` reads the latest revision during queued execution.
6. Join execution reads a locked state snapshot.
7. If no live state exists, queued saved values are used.

## Extension architecture

Python:
- `_RuntimeToggleStringJoinBase.INPUT_COUNT` controls fixed input count.
- New 2/3/5-input variants require only subclasses and mapping entries.

JavaScript:
- The UI discovers `text_N` sockets dynamically.
- Button count and mask width are derived from actual sockets.
- No ten-button list is hard-coded.

## Known constraints

- Server-side live state resets with ComfyUI.
- Workflow-saved state restores and re-syncs after browser loading.
- Same `state_key` is shared across tabs and clients.
- A join that already executed cannot be changed retroactively.
