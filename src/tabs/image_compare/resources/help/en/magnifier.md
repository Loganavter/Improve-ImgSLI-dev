## Magnifier

The magnifier samples a region of the compared pair and shows an enlarged view on the canvas — local detail beyond the split line.

### Turning on the magnifier {#enabling}

- **On/off** — {{tr:image_compare.action.magnifier}} on the toolbar, or `M`.

- **On/off** — {{tr:image_compare.action.magnifier}} on the toolbar, or `M`.
- **Placement** — a click or drag on the image sets the capture area (red circle).
- **Ring style** — capture-ring size and color follow the lens styling.

:::figure{side=block width=280}
![Magnifier lens]({{img:workspace.image_compare.magnifier.enabling}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.magnifier}}.
:::

### Size and movement {#size-and-movement}

- **Lens size** — {{tr:image_compare.label.magnifier_size}}.
- **Capture size** — {{tr:image_compare.label.capture_size}} (how much source area is sampled).
- **Movement** — `WASD` with the lens active; `QE` adjusts the spacing between the halves (the two lens sides) when they are separated.
- **Speed** — {{tr:magnifier.move_speed}} on the magnifier panel when it is shown.

### Freeze {#freeze}

{{tr:image_compare.action.freeze}} (`F`) locks the lens on screen; keyboard nudges keep working while the pointer stays free.

### Divider, guides, and colors {#guides-and-colors}

- **Orientation** — {{tr:image_compare.action.magnifier_orientation}}.
- **Internal divider** — {{tr:image_compare.action.magnifier_divider_combined}} adjusts it via scroll or right-click.
- **Visibility** — {{tr:image_compare.action.magnifier_divider_visible}} and {{tr:image_compare.action.magnifier_guides}} toggle the divider and guides, plus their widths.
- **Colors** — {{tr:image_compare.action.magnifier_colors}} sets per-instance outline colors.

### Multiple instances {#instances}

- **Instance count** — {{tr:image_compare.action.magnifier_instances}} watches several regions.
- **Automatic colors** — new instances get distinct colors when that option is on in Settings.

### Combined mode {#combined-mode}

- **Merging** — the halves merge when dragged together.
- **Splitting inside** — a drag with `RMB` inside the lens splits them.
- **Side forcing** — `Space+Shift` forces one side inside the combined lens.

:::figure{side=block width=280}
![Combined magnifier]({{img:workspace.image_compare.magnifier.combined_mode}})
{{tr:image_compare.action.magnifier}} combined mode.
:::

For a full-canvas compare without the lens, see [Comparison](help://comparison).

### Toolbar in this tab {#toolbar}

The magnifier buttons on the toolbar depend on {{tr:settings.ui_mode}}: beginner keeps nine separate buttons (magnifier, instances, freeze, orientation, divider visibility, colors, divider width, guides, guides width); advanced and expert keep six combined ones; minimal keeps two (magnifier, instances). The rest runs through {{tr:menu.find_action}}.

### Settings that affect the magnifier {#related-settings}

Magnifier-related options live under [Settings](help://settings#image_compare):

- Faster movement and its interpolation
- Intersection highlights between lenses
- Automatic colors for new instances
