# Runtime and Optional Join test checklist

## Optional String Join

1. All inputs unconnected -> empty string
2. One connected input -> that string only
3. Empty string plus non-empty string -> no stray separator
4. Upstream source Bypass -> missing input is ignored
5. Whitespace-only input -> preserved
6. Embedded line breaks -> preserved

## Runtime Toggle String Join

1. Load workflow and confirm a synced revision is shown
2. Queue several jobs with all toggles ON
3. During generation, turn one input OFF
4. Confirm the next image onward omits that input
5. Change `multiple` to `single`
6. Confirm only the last selected input remains enabled
7. Click the active single-mode button
8. Confirm all inputs are OFF and output is an empty string
9. Return to `multiple` and enable multiple inputs
10. Save, close, reopen, and confirm mode and toggles are restored
11. Queue PromptRandomChoice outputs and confirm random values still reach the join
12. Connect the same output to CLIP and JPEG comment, then confirm they match

## Failure fallback

1. Temporarily break the live-state route
2. Confirm the node reports live sync failure
3. Confirm queued saved mode and mask are still used
