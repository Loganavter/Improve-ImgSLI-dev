## Image Properties

File metadata and in-app context for one loaded image. The dialog opens over the session and changes nothing in it.

:::figure{side=block width=280}
![Image Properties dialog]({{img:platform.image_properties.open}})
{{tr:image_properties.title}}.
:::

### Open the dialog {#open}

The {{tr:image_compare.action.context_properties}} entry in the image context menu opens {{tr:image_properties.title}} for that image. The {{tr:recent.action_properties}} entry in the recent-projects context menu opens it for that project.

### Sections {#sections}

Rows are grouped into:

- {{tr:image_properties.section_file}} — file name, location, and file details
- {{tr:image_properties.section_image}} — core image details
- {{tr:image_properties.section_app}} — how the session places this image (see below)
- {{tr:image_properties.section_metadata}} — camera / EXIF-style fields when the file provides them

The dialog hides empty rows and drops a section left with no values; it marks a file read error as {{tr:image_properties.read_error}}.

### In-app context {#in-app}

{{tr:image_properties.section_app}} shows how the session places the image (side, position, rating — depending on the session type). These rows are session state, not the file.

### Close {#close}

{{tr:image_properties.close}} dismisses the dialog. {{tr:image_properties.copy_all}} copies every visible row to the clipboard; to copy part of the page, select it and use {{tr:action.context_copy}} (or {{tr:action.context_select_all}} first).
