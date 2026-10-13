## Comparison

Two images on the full canvas with a movable split, filename labels, channel views, and difference modes. The page for full-frame pair inspection; local detail lives in the [Magnifier](help://magnifier).

### Split line {#split-line}

With the magnifier off, the divider moves across the pair.

- **Orientation** — {{tr:image_compare.action.divider_orientation}} switches horizontal / vertical.
- **Width** — scroll over {{tr:image_compare.action.divider_width}} changes the thickness.
- **Color** — {{tr:image_compare.action.divider_color}} sets the color.
- **Visibility** (`D`) — {{tr:image_compare.action.divider_visible}} shows or hides the line.
- **Three settings in one** — {{tr:image_compare.action.divider_combined}} joins orientation, width, and color (scroll / right-click / middle-click); all gestures: [Buttons and Controls](help://ui.buttons#multi-action).

:::figure{side=block width=280}
![Split line]({{img:workspace.image_compare.comparison.split_line}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.divider}}.
:::

### Image scrolling {#scroll-images}

- **One side** — the wheel over the canvas steps the list on the side under the cursor (left of a vertical split / above a horizontal split = side 1; the other half = side 2).
- **Both sides** — `Shift` + wheel steps both lists together.
- **Single-side preview** — with a single-image preview, the wheel always steps the visible side.
- **From the dropdown** — the wheel over a dropdown steps that side without opening the panel; see [Lists and Panels](help://ui.lists_flyouts#scroll-lists).
- **Swap** (`X`) — a short click exchanges the current pair; a long-press swaps both lists.

### Filename labels {#labels-and-metrics}

- **Names** (`N`) — {{tr:image_compare.action.file_names}}; enabled names can burn into exports.
- **Hidden while zoomed** — labels hide while zoomed in and return at fit zoom.
- **Text style** — {{tr:image_compare.action.text_settings}} opens a panel for size, weight, opacity, colors, background, and placement.

### Difference metrics {#metrics}

- **{{tr:image_compare.ui.psnr}} / {{tr:image_compare.ui.ssim}}** — off by default; the automatic readout lives in [Settings](help://settings#image_compare) under {{tr:workspace.session_types.image_compare}}.

### Context menu actions {#context-menu-actions}

- **Properties** — [Image Properties](help://image_properties) from a list-row context menu (file metadata and in-app side / rating).
- **Move** — from the canvas or list context menu, a preview of the image follows the pointer. A click on another workspace tab or the canvas places it, as with Duplicate or paste. `Esc` or right-click cancels.

### Channel modes {#channel-modes}

{{tr:image_compare.action.channel_mode}} (`C`) cycles RGB, R, G, B, and luminance for single-channel inspection without leaving the canvas.

### Difference modes {#difference-modes}

{{tr:image_compare.action.diff_mode}} (`H` cycles) emphasizes where the pair differs:

:::figure{side=block width=280}
![Difference mode]({{img:workspace.image_compare.comparison.difference_modes}})
{{tr:image_compare.action.diff_mode}}.
:::

- **{{tr:image_compare.action.diff_highlight}}** — change regions highlighted on the live pair
- **{{tr:image_compare.action.diff_grayscale}}** — intensity differences desaturated
- **{{tr:image_compare.action.diff_edges}}** — edge-oriented differences traced
- **{{tr:image_compare.action.diff_ssim}}** — structural similarity mapped when metrics support it

Difference modes combine with channel views. For local inspection, the [Magnifier](help://magnifier).

### Toolbar in this tab {#toolbar}

The split-line buttons on the toolbar depend on {{tr:settings.ui_mode}}: beginner keeps four separate buttons (orientation, visibility, color, width); advanced keeps two (orientation, color); expert and minimal keep one (orientation). Shared gestures from [Buttons and Controls](help://ui.buttons#multi-action) apply here: scroll changes the divider thickness, right-click sets the color, middle-click resets, long-press on list buttons clears or swaps lists. In minimal, the rest runs through {{tr:menu.find_action}}.
