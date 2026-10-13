## Magnifier

The magnifier samples a region of the compared pair and shows an enlarged view on the canvas — local detail beyond the split line.

### Enabling {#enabling}

- **Turn on** — {{tr:image_compare.action.magnifier}} on the toolbar, or `M`.
- **Click to place** — click or drag on the image to set the capture area (red circle).
- **Style the ring** — capture-ring size and color follow the lens styling.

:::figure{side=block width=280}
![Magnifier lens]({{img:workspace.image_compare.magnifier.enabling}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.magnifier}}.
:::

### Size and movement {#size-and-movement}

- **Change the lens size** — {{tr:image_compare.label.magnifier_size}}.
- **Change the capture size** — {{tr:image_compare.label.capture_size}} (how much source area is sampled).
- **Move** — `WASD` with the lens active; `QE` adjusts the spacing between the halves (the two lens sides) when they are separated.
- **Adjust the speed** — {{tr:magnifier.move_speed}} on the magnifier panel when it is shown.

### Freeze {#freeze}

{{tr:image_compare.action.freeze}} (`F`) locks the lens on screen; keyboard nudges keep working while the pointer stays free.

### Divider, guides, and colors {#guides-and-colors}

- **Flip orientation** — {{tr:image_compare.action.magnifier_orientation}}.
- **Scroll or right-click** — {{tr:image_compare.action.magnifier_divider_combined}} adjusts the internal divider.
- **Show or hide** — {{tr:image_compare.action.magnifier_divider_visible}} and {{tr:image_compare.action.magnifier_guides}} toggle the divider and guides, plus their widths.
- **Pick colors** — {{tr:image_compare.action.magnifier_colors}} sets per-instance outline colors.

### Multiple instances {#instances}

- **Add or remove** — {{tr:image_compare.action.magnifier_instances}} watches several regions.
- **Recolor automatically** — new instances get distinct colors when that option is on in Settings.

### Combined mode {#combined-mode}

- **Merge** — Drag the halves together to merge.
- **Split inside** — drag with `RMB` inside the lens.
- **Force one side** — `Space+Shift` forces one side inside the combined lens.

:::figure{side=block width=280}
![Combined magnifier]({{img:workspace.image_compare.magnifier.combined_mode}})
{{tr:image_compare.action.magnifier}} combined mode.
:::

For a full-canvas compare without the lens, see [Comparison](help://comparison).

### Toolbar in this tab {#toolbar}

The magnifier buttons on the toolbar depend on {{tr:settings.ui_mode}}: beginner keeps nine separate buttons (magnifier, instances, freeze, orientation, divider visibility, colors, divider width, guides, guides width); advanced and expert keep six combined ones; minimal keeps two (magnifier, instances). The rest runs through {{tr:menu.find_action}}.

### Settings that affect the magnifier {#related-settings}

Magnifier-related options live under [Settings](help://settings#image_compare):

- Speed up movement and its interpolation
- Highlight intersections between lenses
- Recolor new instances automatically
