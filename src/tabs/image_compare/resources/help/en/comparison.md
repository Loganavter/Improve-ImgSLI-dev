## Comparison

Two images on the full canvas: a movable split, optional filename labels, channel views, and difference modes — without opening the magnifier. Live canvas, export stills, and video recording keep the same look.

### Split line {#split-line}

With the magnifier off, drag the divider across the pair.

- **Flip orientation** — {{tr:image_compare.action.divider_orientation}} switches horizontal / vertical.
- **Change width** — scroll over {{tr:image_compare.action.divider_width}}.
- **Pick a color** — {{tr:image_compare.action.divider_color}}.
- **Show or hide** (`D`) — {{tr:image_compare.action.divider_visible}} toggles the line.
- **Pack three controls into one** — {{tr:image_compare.action.divider_combined}} joins orientation, width, and color (scroll / right-click / middle-click); all gestures: [Buttons and Controls](help://ui.buttons#multi-action).

:::figure{side=block width=280}
![Split line]({{img:workspace.image_compare.comparison.split_line}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.divider}}.
:::

### Scroll through images {#scroll-images}

- **Step one side** — wheel over the canvas steps the list on the side under the cursor (left of a vertical split / above a horizontal split = side 1; the other half = side 2).
- **Step both sides** — `Shift` + wheel steps both lists together.
- **Preview one side** — with a single-image preview, the wheel always steps the visible side.
- **Step from the dropdown** — wheel over a dropdown steps that side without opening the panel; see [Lists and Panels](help://ui.lists_flyouts#scroll-lists).
- **Swap** (`X`) — short click exchanges the current pair; long-press swaps both lists.

### Labels {#labels-and-metrics}

- **Show names** (`N`) — {{tr:image_compare.action.file_names}}; can burn into exports when enabled.
- **Hide while zoomed** — labels hide while zoomed in and return at fit zoom.
- **Style the text** — {{tr:image_compare.action.text_settings}} opens a panel for size, weight, opacity, colors, background, and placement.

### Metrics {#metrics}

- **Turn on {{tr:image_compare.ui.psnr}} / {{tr:image_compare.ui.ssim}}** — off by default; turn on the automatic readout in [Settings](help://settings#image_compare) under {{tr:workspace.session_types.image_compare}}.

### Context menu actions {#context-menu-actions}

- **Inspect properties** — open [Image Properties](help://image_properties) from a list-row context menu (file metadata and in-app side / rating).
- **Move** — from the canvas or list context menu, a preview of the image follows the pointer. Click another workspace tab or the canvas to place it, as with Duplicate or paste. `Esc` or right-click cancels.

### Channel modes {#channel-modes}

{{tr:image_compare.action.channel_mode}} (`C`) cycles RGB, R, G, B, and luminance for single-channel inspection without leaving the canvas.

### Difference modes {#difference-modes}

{{tr:image_compare.action.diff_mode}} (`H` cycles) emphasizes where the pair differs:

:::figure{side=block width=280}
![Difference mode]({{img:workspace.image_compare.comparison.difference_modes}})
{{tr:image_compare.action.diff_mode}}.
:::

- **{{tr:image_compare.action.diff_highlight}}** — highlight change regions on the live pair
- **{{tr:image_compare.action.diff_grayscale}}** — desaturate intensity differences
- **{{tr:image_compare.action.diff_edges}}** — trace edge-oriented differences
- **{{tr:image_compare.action.diff_ssim}}** — map structural similarity when metrics support it

Difference modes combine with channel views. For local inspection, use the [Magnifier](help://magnifier).

### Toolbar in this tab {#toolbar}

The split-line buttons on the toolbar depend on {{tr:settings.ui_mode}}: beginner keeps four separate buttons (orientation, visibility, color, width); advanced keeps two (orientation, color); expert and minimal keep one (orientation). Shared gestures from [Buttons and Controls](help://ui.buttons#multi-action) apply here: scroll to change the divider thickness, right-click for color, middle-click to reset, long-press list buttons to clear or swap lists. In minimal, the rest runs through {{tr:menu.find_action}}.
