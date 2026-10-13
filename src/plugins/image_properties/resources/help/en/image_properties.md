## Image Properties

File metadata and in-app context for one loaded image. The dialog floats above the session and changes nothing in it.

:::figure{side=block width=280}
![Image Properties dialog]({{img:platform.image_properties.open}})
{{tr:image_properties.title}}.
:::

### Open the dialog {#open}

The {{tr:image_compare.action.context_properties}} entry in a list or slot context menu opens {{tr:image_properties.title}} for that image. The {{tr:recent.action_properties}} entry in the recent-projects context menu opens it for that project.

### Sections {#sections}

Rows are grouped into:

- {{tr:image_properties.section_file}} — name, path, extension, size on disk, format, modified time
- {{tr:image_properties.section_image}} — pixel size, megapixels, aspect, orientation, channels, DPI and color mode / profile when available
- {{tr:image_properties.section_app}} — how the app places this image in the current session (see below)
- {{tr:image_properties.section_metadata}} — camera / EXIF-style fields when the file provides them

Empty rows are omitted, and a section left with no values is hidden entirely; a file read error appears as {{tr:image_properties.read_error}}.

### In-app context {#in-app}

{{tr:image_properties.section_app}} depends on where the dialog was opened. An {{tr:workspace.session_types.image_compare}} entry carries {{tr:image_properties.side}} (left / right) and {{tr:image_properties.rating}}. A {{tr:workspace.session_types.multi_compare}} cell carries {{tr:image_properties.position}}. A recent project carries its own bookkeeping instead — dates, last opened, session types. Those rows describe session state, not the file on disk.

### Close {#close}

{{tr:image_properties.close}} dismisses the dialog. {{tr:image_properties.copy_all}} copies every visible row to the clipboard; to copy part of the page, select it and use {{tr:action.context_copy}} (or {{tr:action.context_select_all}} first).
