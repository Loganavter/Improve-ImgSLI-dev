## Settings

Application behavior in one dialog: built-in pages plus sections contributed by other components. Contributed sections stay visible regardless of the active session.

Comparison options live in the [Comparison](help://comparison) help. Gallery AI settings live in the [Image Gallery](help://gallery_ask_ai) help.

### Settings opening {#open-settings}

- **Menu** — {{tr:menu.settings}} (`Ctrl+,`).
- **Toolbar** — the settings button at the top of the toolbar.
- **Find Action** — `Ctrl+Shift+P` ({{tr:menu.find_action}}) plus a page name ({{tr:settings.general}}, {{tr:settings.appearance}}, {{tr:settings.keyboard}}, …).
- **{{tr:action.palette.learn_more}}** — the help topic for a settings action, when one exists.
- **{{tr:common.ok}}** — the current values applied, the dialog left open.
- **{{tr:common.cancel}}** — the dialog closed.
- **Esc** — never closes the Settings dialog; it clears the in-dialog search when one is active.

### Search inside Settings {#search}

Text in the search field above the sidebar. Each matching section appears as one row, however deep the match sits (an option name, a group title, any language). An activated row opens that section with the matched options highlighted. `Esc` clears the search and restores the full sidebar.

### General {#general}

- **{{tr:label.language}}** — en / ru / zh / pt_BR.
- **{{tr:label.theme}}** — auto / light / dark.
- **{{tr:settings.system_notifications}}** — OS-level notification toggle.
- **{{tr:settings.enable_debug_logging}}** — verbose logs for troubleshooting.

### Appearance {#interface}

- **{{tr:settings.ui_mode}}** — {{tr:settings.ui_mode_beginner}} / {{tr:settings.ui_mode_advanced}} / {{tr:settings.ui_mode_expert}} radios; beginner mode is selected by default.
- **{{tr:settings.ui_font}}** — the builtin, system default, or a custom family.
- **{{tr:settings.ui_scale}}** — the interface scale slider.
- **Limits** — caps on displayed values.

### Performance {#performance}

- **{{tr:settings.render_backend_label}}** — the available set depends on the system; switching applies on next launch.

### Keyboard {#keyboard}

- **Grouping** — shortcuts grouped by owner.
- **Resetting** — one shortcut or all.
- **Fixed** — canvas `WASD` and `Space` stay fixed — see [Hotkeys](help://hotkeys).
