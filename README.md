# ComfyUI-StringJoinTools

Focused STRING join and inspection nodes for ComfyUI.

## Category

`String Join Tools`

## Nodes

- Optional String Join (2)
- Optional String Join (3)
- Optional String Join (5)
- Optional String Join (10)
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

All Optional and Runtime Toggle variants support these limited separator escape
sequences:

| Input | Actual separator |
| --- | --- |
| `\n` | Line feed (LF) |
| `\r\n` | Windows newline (CRLF) |
| `\t` | Tab |
| `\\` | One backslash |
| `\\n` | The literal characters `\n` |

Unsupported sequences such as `\u` and `\x` are preserved literally.

## Runtime Toggle String Join

These nodes are available with 2, 3, 5, or 10 inputs and are intended for long,
pre-queued generation runs.

Queued upstream nodes still produce their STRING values normally. This includes
runtime outputs from nodes such as PromptRandomChoice. When the join node executes,
it reads the latest live mode and toggle state from the ComfyUI server, then joins
only the currently enabled non-empty strings.

This allows LoRA, seed, character, and other job-specific settings to be queued in
advance while the prompt composition can still be changed during generation.

<img width="575" height="657" alt="image" src="https://github.com/user-attachments/assets/a12cdcab-d352-4549-b537-54f68188c523" />

### Modes

- `multiple`: Every input toggle is independent.
- `single`: Zero or one input can be enabled. Clicking the active input turns all
  inputs off.

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
