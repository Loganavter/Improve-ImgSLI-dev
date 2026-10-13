## Multi Compare Export

The grid saves as one image through quick save or the save dialog. A session keeps its grid, so reopening the session brings the layout back.

### Save and export {#save-and-export}

- **Quick save** (`Ctrl+S`) — {{tr:multi_compare.action.quick_save}} writes the image with the last-used settings, without a dialog. Quick save sits on the toolbar in every density except minimal; the full dialog opens from the footer bar or {{tr:menu.find_action}}.
- **Save dialog** — {{tr:multi_compare.action.save}} via {{tr:menu.find_action}}; see [Export](help://export).
- **Grid match** — the saved image matches the on-screen grid at tested sizes; very large exports are untested (see below).
- **Crop first** — each slot's crop is applied before the slots are combined.
- **Empty slots skipped** — slots without an image are left out of the saved image.
- **Large-export confirmation** — if the longer side is over 16384 px, a warning asks whether to continue. Sizes beyond that have not been tested, so the export may fail or run out of memory. Cancel stops the export. Checking "Don't show again" turns the warning off for later exports.

### Sessions {#sessions}

A session stores the slot image paths and labels, the layout, the focused slot, zoom and pan, and the label and divider styling.

- **Reopening** — a session shows its slots when it opens. Its images load again from their file paths; a session that is not active loads its images on switch to it.
- **New sessions** — a new session starts with the last-used divider and label styling.
