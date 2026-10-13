## Multi Compare Layouts

Slots sit in a split grid with per-cell drops, gap splits, and draggable dividers.

### Cells and drop zones {#layouts}

- **Grid** — slots take file drops or {{tr:multi_compare.action.add_images}} (`Ctrl+O`).
- **Empty slots** — stay open for new drops.
- **Outside drops** — file-manager drops, clipboard paste, or **Move** from another tab auto-place with a loading notification.
- **Auto-place** — new images split the largest cell along its longer axis.
- **Rearrange** — drag a slot onto another slot to swap them; drop into a gap to insert between; see [Gap split zones](#gap-split-zones).
- **Layout change** — keeps loaded images.

### Gap split zones {#gap-split-zones}

Drop into a divider gap to split a new cell between the neighbours; a drop at the outer edge places outside the row or column.

### Dividers {#dividers}

- **Drag** — moves a divider and changes the relative size of the cells on either side.
- **Reset** — double-click a divider to make the cells on either side equal.
- **Visibility** (`D`) — {{tr:multi_compare.action.divider_visible}}.
- **Color / width** — {{tr:multi_compare.action.divider_color}} and {{tr:multi_compare.action.divider_width}}.

### Slot actions {#context-menu}

Per-image actions:

- **Rename** — edits the slot label.
- **Duplicate** — copies the slot; needs a loaded image and a free slot.
- **Properties** — [Image Properties](help://image_properties) with file metadata and grid position.
- **Move** — drags the image onto another tab, where it loads and is placed automatically.
- **Crop** — turns crop on or off for this slot; see [Viewing](help://mc_viewing#slot-crop).
- **Remove** — drops the slot from the grid.
