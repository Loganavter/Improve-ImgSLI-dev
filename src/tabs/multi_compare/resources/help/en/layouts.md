## Multi Compare Layouts

Slots in a split grid, new cells split from divider gaps, and dividers resized by drag.

### Cells and drop zones {#layouts}

- **Grid filling** — slots take file drops or {{tr:multi_compare.action.add_images}} (`Ctrl+O`).
- **Empty slots** — they stay open for new drops.
- **Outside drops** — file-manager drops, clipboard paste, or **Move** from another tab auto-place with a loading notification.
- **Automatic placement** — new images split the largest cell along its longer axis.
- **Rearranging** — a slot dragged onto another slot swaps them; a drop into a gap inserts between; see [Gap split zones](#gap-split-zones).
- **Images kept on layout change** — changing the layout keeps loaded images.

### Gap split zones {#gap-split-zones}

A drop into a divider gap splits a new cell between the neighbours; a drop at the outer edge places outside the row or column. The grid picture lives on the [Overview](help://multi_compare) page.

### Dividers {#dividers}

- **Dragging** — moves a divider and changes the relative size of the cells on either side.
- **Double-click reset** — makes the cells on either side equal.
- **Visibility toggle** (`D`) — {{tr:multi_compare.action.divider_visible}}.
- **Color and width** — {{tr:multi_compare.action.divider_color}} and {{tr:multi_compare.action.divider_width}}.

### Slot actions {#context-menu}

Per-image actions:

- **Label rename** — edits the slot label.
- **Duplicate** — copies the slot; needs a loaded image and a free slot.
- **Property inspection** — [Image Properties](help://image_properties) with file metadata and grid position.
- **Move to another tab** — the image dragged onto another tab, where it loads and is placed automatically.
- **Crop toggle** — turns crop on or off for this slot; see [Viewing](help://mc_viewing#slot-crop).
- **Removal** — drops the slot from the grid.

### Toolbar in this tab {#toolbar}

The toolbar buttons depend on {{tr:settings.ui_mode}}: beginner keeps three divider buttons (visibility, color, width); advanced keeps two (color, width); expert keeps one (width); minimal keeps none. Label text settings stay on the toolbar in every density; see [Viewing](help://mc_viewing).
