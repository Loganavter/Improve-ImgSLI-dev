## Export

Still-image export of the current canvas. Session capture and video encoding are a separate topic: [Video Editor](help://video).

:::figure{side=block width=630}
![Export dialog]({{img:workspace.image_compare.export.dialog}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.export}}.
:::

### Still saving {#saving-an-image}

The dialog opens from the {{tr:image_compare.action.save}} button on the toolbar, or through {{tr:menu.find_action}}.

- **Path** — the output directory and file name.
- **Format** — a format from the list.
- **Preview** — the composed result in the preview before writing.

### Resolution and quality {#resolution-and-quality}

- **Size** — the frame size.
- **Quality** — {{tr:label.quality}} appears when it applies to the format.
- **PNG** — the compression level and {{tr:export.optimize_png}}.
- **Fill** — {{tr:export.fill_background}} paints the empty margins around the image; {{tr:export.background_color}} picks the paint color. Where there is nothing to fill, the option is unavailable.

### Metadata and favorites {#metadata-and-favorites}

- **Metadata** — {{tr:export.include_metadata}} stays on unless switched off; the comment field hides with it. {{tr:export.remember_by_default}} keeps the comment text for the next export.
- **Favorites** — {{tr:misc.set_as_favorite}} pins the current directory; {{tr:tooltip.use_favorite}} recalls it.
- **Labels** — when {{tr:image_compare.action.file_names}} is on, names render into the still as session state, not file data.

### Quick save {#quick-save}

- **`Ctrl+S`** — {{tr:image_compare.action.quick_save}} reuses the last export settings without opening the dialog.
