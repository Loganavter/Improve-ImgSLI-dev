## Multi Compare Layouts

Fill slots in a split grid, split new cells from divider gaps, and drag dividers to resize.

### Cells and drop zones {#layouts}

- **Fill the grid** — slots take file drops or {{tr:multi_compare.action.add_images}} (`Ctrl+O`).
- **Keep empty slots open** — they stay open for new drops.
- **Drop from outside** — file-manager drops, clipboard paste, or **Move** from another tab auto-place with a loading notification.
- **Place automatically** — new images split the largest cell along its longer axis.
- **Rearrange** — drag a slot onto another slot to swap them; drop into a gap to insert between; see [Gap split zones](#gap-split-zones).
- **Keep images on layout change** — changing the layout keeps loaded images.

### Gap split zones {#gap-split-zones}

Drop into a divider gap to split a new cell between the neighbours; a drop at the outer edge places outside the row or column. The grid picture lives on the [Overview](help://multi_compare) page.

### Dividers {#dividers}

- **Drag** — moves a divider and changes the relative size of the cells on either side.
- **Double-click to reset** — makes the cells on either side equal.
- **Toggle visibility** (`D`) — {{tr:multi_compare.action.divider_visible}}.
- **Recolor or resize** — {{tr:multi_compare.action.divider_color}} and {{tr:multi_compare.action.divider_width}}.

### Slot actions {#context-menu}

Per-image actions:

- **Rename the label** — edits the slot label.
- **Duplicate** — copies the slot; needs a loaded image and a free slot.
- **Inspect properties** — open [Image Properties](help://image_properties) with file metadata and grid position.
- **Move to another tab** — drags the image onto another tab, where it loads and is placed automatically.
- **Toggle crop** — turns crop on or off for this slot; see [Viewing](help://mc_viewing#slot-crop).
- **Remove** — drops the slot from the grid.

### Toolbar in this tab {#toolbar}

The toolbar buttons depend on {{tr:settings.ui_mode}}: beginner keeps three divider buttons (visibility, color, width); advanced keeps two (color, width); expert keeps one (width); minimal keeps none. Label text settings stay on the toolbar in every density; see [Viewing](help://mc_viewing).
