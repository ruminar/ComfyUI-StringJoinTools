# Runtime and Optional Join test checklist

## Optional String Join

1. All inputs unconnected -> empty string
2. One connected input -> that string only
3. Empty string plus non-empty string -> no stray separator
4. Upstream source Bypass -> missing input is ignored
5. Whitespace-only input -> preserved
6. Embedded line breaks -> preserved
7. Separator `\n` -> LF between joined strings
8. Separator `\r\n` -> CRLF between joined strings
9. Separator `\t` -> tab between joined strings
10. Separator `\\n` -> literal `\n` between joined strings

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
13. Turn an input OFF and confirm its complete `text_n` row is filled in bypass purple
14. Turn it ON again and confirm the purple row fill disappears
15. Save and reopen the workflow and confirm the purple rows match the restored toggles
16. Hover the clickable part of an ON and OFF row and confirm it becomes slightly brighter
17. Left-click the center of a row beyond both socket safety zones and confirm it toggles
18. Click or drag within 60 px of the input side or 45 px of the output side and confirm the row does not toggle
19. Drag by more than 5 px within a row and confirm it does not toggle
20. Right-click a row and confirm the normal ComfyUI context operation is preserved
21. Confirm the ten lower toggle buttons still work
22. Resize the node smaller, switch workflow tabs, and confirm its size is preserved
23. Save and reload the workflow and confirm the custom node size is preserved

## String Output

1. Resize the node smaller, switch workflow tabs, and confirm its size is preserved
2. Save and reload the workflow and confirm its size is preserved

## Failure fallback

1. Temporarily break the live-state route
2. Confirm the node reports live sync failure
3. Confirm queued saved mode and mask are still used
