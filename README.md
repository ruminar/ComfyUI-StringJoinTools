# ComfyUI-StringJoinTools

Focused STRING join and inspection nodes for ComfyUI.

## Category

`String Join Tools`

## Nodes

- Optional String Join (2)
- Optional String Join (3)
- Optional String Join (5)
- Optional String Join (10)
- Toggle String Join (2)
- Toggle String Join (3)
- Toggle String Join (5)
- Toggle String Join (10)
- Runtime Toggle String Join (2)
- Runtime Toggle String Join (3)
- Runtime Toggle String Join (5)
- Runtime Toggle String Join (10)
- String Output

## Optional String Join

- Numbered STRING sockets are optional.
- Unconnected inputs are ignored.
- Inputs missing because an upstream source is bypassed are accepted.
- Exact empty strings are ignored.
- Whitespace and embedded line breaks are preserved.
- The separator is inserted only between usable strings.
- If every input is missing or empty, the node returns `""`.

For more inputs, connect join nodes in stages.

<img width="582" height="466" alt="image" src="https://github.com/user-attachments/assets/791980b1-8f51-49f0-ab20-06468d887cac" />

## Separator escapes

All Optional, Toggle, and Runtime Toggle variants support these limited
separator escape sequences:

| Input | Actual separator |
| --- | --- |
| `\n` | Line feed (LF) |
| `\r\n` | Windows newline (CRLF) |
| `\t` | Tab |
| `\\` | One backslash |
| `\\n` | The literal characters `\n` |

Unsupported sequences such as `\u` and `\x` are preserved literally.

## Toggle String Join

These nodes are available with 2, 3, 5, or 10 inputs. Connected inputs can be
enabled or disabled using the buttons or by left-clicking their input rows.

The toggle state and mode are captured when the prompt is queued. Later UI
changes do not affect jobs already waiting in the queue. This variant is suited
to unattended batch generation after the desired prompt composition is chosen.

- `multiple`: Every input toggle is independent.
- `single`: Zero or one input can be enabled.

The status area displays `QUEUE SNAPSHOT`.

<img width="540" height="598" alt="image" src="https://github.com/user-attachments/assets/8bfb37e7-c2f2-4cf4-91d7-d26ff40071ca" />

## Runtime Toggle String Join

These nodes are available with 2, 3, 5, or 10 inputs and are intended for long,
pre-queued generation runs.

Queued upstream nodes still produce their STRING values normally. This includes
runtime outputs from nodes such as PromptRandomChoice. When the join node executes,
it reads the latest live mode and toggle state from the ComfyUI server, then joins
only the currently enabled non-empty strings.

This allows LoRA, seed, character, and other job-specific settings to be queued in
advance while the prompt composition can still be changed during generation.

<img width="561" height="617" alt="image" src="https://github.com/user-attachments/assets/f9a37b43-5af4-444c-95fe-f63d6615e15a" />

### Modes

- `multiple`: Every input toggle is independent.
- `single`: Zero or one input can be enabled. Clicking the active input turns all
  inputs off.

Runtime variants use a subtle amber background tint and display `LIVE` in their
status area.

### Saved and live state

The following values are saved in the workflow:

- mode
- enabled toggle mask
- last selected input
- persistent state key

Changing a toggle or the mode updates both the workflow-saved state and the
server-side live state. Jobs already waiting in the queue read the latest server
state when this node executes.

If live state is unavailable, queued saved values are used as a safe fallback.

### Cache behavior

The live state has a monotonic revision number. The node includes this revision
in `IS_CHANGED`, so changing a live toggle or mode invalidates the cached join
result and downstream processing.

### Timing

A change affects jobs whose Runtime Toggle String Join has not executed yet.
For normal image workflows, treat this as "the next image onward."

### Metadata

Connect the same Runtime Toggle String Join output to both CLIP Text Encode and
the JPEG comment/metadata input of the saver to preserve the exact prompt used.

### Browser tabs

Live state is shared by `state_key` on the ComfyUI server. Use one active browser
tab for controlling a given workflow.

## String Output

Displays the received text, explicit empty-string status, and character count.
The same STRING is returned unchanged.

<img width="356" height="270" alt="image" src="https://github.com/user-attachments/assets/8afa3b1a-3dfe-4a96-8791-b67c7d6fe3f1" />


## Installation

Extract the folder into:

`ComfyUI/custom_nodes/`

Restart ComfyUI and refresh the browser.

No additional Python packages are required.
