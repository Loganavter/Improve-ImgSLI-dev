## Lists and Panels

Dropdowns open in-window panels over the main window. An outside click or `Esc` dismisses the panel. Toolbar layout and multi-action gestures: [Buttons and Controls](help://ui.buttons). Filename label styling: [Comparison](help://comparison).

### List manager {#list-manager}

In a {{tr:workspace.session_types.image_compare}} session each side has a list dropdown. A click opens that side's list-manager panel; the panel stays closed if the list is empty. The same dropdown, an outside click, or a row pick closes it.

:::figure{side=block width=320}
![List manager panel]({{img:ui.lists_flyouts.list_manager}})
List dropdown → list-manager panel.
:::

### Toolbar buttons {#quick-list-actions}

Buttons beside each dropdown add, swap, or remove images on that side. Short click versus long-press depends on the UI mode — [Buttons and Controls](help://ui.buttons#multi-action).

### Rows {#rows}

- **Select** — click a row to make it current; the panel closes and the canvas updates. `Ctrl`/`Cmd`+click toggles rows for a multi-selection.
- **Move** — drag rows to reorder one list or move them to the other list.
- **Path tip** — hover a truncated name to see the full path.

### Rating {#rating}

Change the row score with the minus / plus buttons or a scroll over the chip, without leaving the panel.

### Context menu {#context-menu}

Right-click a list row or the current canvas frame for its action menu — properties, path, and list-membership actions. Properties opens [Image Properties](help://image_properties).

### Scroll {#scroll-lists}

The wheel steps images without opening the panel — full rules: [Comparison → Scroll through images](help://comparison#scroll-images).

### Loading {#loading}

Files and clipboard images land in the session lists — full rules: [Files and Projects](help://file_management#loading-images).

### Label settings panel {#toolbar-flyouts}

The panel opens from {{tr:image_compare.action.text_settings}} or a right-click on {{tr:image_compare.action.file_names}}; `Esc` or an outside click closes it.

The panel covers font size, weight, opacity, text and background colors, draw-background, and label placement (edges / split line).

:::figure{side=block width=280}
![Label settings panel]({{img:ui.lists_flyouts.toolbar_flyouts}})
{{tr:image_compare.action.text_settings}}.
:::

Split-line color and magnifier option panels are separate — [Comparison](help://comparison) and [Magnifier](help://magnifier).

### {{tr:workspace.session_types.multi_compare}} {#multi-compare}

A {{tr:workspace.session_types.multi_compare}} session has no dual-list panel — images go into grid slots. Label text settings still open a panel (without the placement radios from {{tr:workspace.session_types.image_compare}}). Details: [{{tr:workspace.session_types.multi_compare}}](help://multi_compare).
