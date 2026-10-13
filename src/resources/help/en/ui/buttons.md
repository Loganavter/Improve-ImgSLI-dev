## Buttons and Controls

The toolbar sits at the top and holds the action buttons you need.

### The toolbar {#toolbar}

- **Toolbar** — strip of buttons at the top for the active tab.
- **Contents** — each tab brings its own set: compare tabs hold split line, view modes, magnifier, recording; the gallery holds folder, filter, sorting. The session picker has no toolbar.
- **Density** — in compare tabs follows {{tr:settings.ui_mode}}; other tabs keep a fixed set.

:::figure{side=block height=107}
![Session toolbar]({{img:ui.buttons.toolbar}})
Toolbar above the canvas.
:::

### UI modes {#ui-modes}

The same tools are laid out differently in each {{tr:settings.ui_mode}}. Modes apply to the compare tabs; the gallery and session picker keep a fixed set. First-run onboarding sets the mode once; [Settings → Appearance](help://settings#interface) changes it later.

### {{tr:settings.ui_mode_beginner}} {#mode-beginner}

More separate buttons — one button, one action.

:::figure{side=block height=65}
![Beginner toolbar layout]({{img:ui.buttons.mode_beginner}})
{{tr:settings.ui_mode}} → {{tr:settings.ui_mode_beginner}}.
:::

### {{tr:settings.ui_mode_advanced}} {#mode-advanced}

Fewer icons. Some buttons already combine a short click with a scroll (for example orientation + thickness).

:::figure{side=block height=65}
![Advanced toolbar layout]({{img:ui.buttons.mode_advanced}})
{{tr:settings.ui_mode}} → {{tr:settings.ui_mode_advanced}}.
:::

### {{tr:settings.ui_mode_expert}} {#mode-expert}

Densest strip: one button combines click, scroll, and other mouse buttons.

:::figure{side=block height=65}
![Expert toolbar layout]({{img:ui.buttons.mode_expert}})
{{tr:settings.ui_mode}} → {{tr:settings.ui_mode_expert}}.
:::

### Minimal {#mode-minimal}

Fewest buttons — the essentials only; everything else stays reachable through {{tr:menu.find_action}}.

### Multi-action controls {#multi-action}

In {{tr:settings.ui_mode_advanced}} and especially {{tr:settings.ui_mode_expert}}, the same icon often does more than one thing:

- **Short click** — primary action or toggle.
- **Scroll** — nudge a numeric value (divider thickness, magnifier size, …) without opening a dialog.
- **Long-press** — stronger variant on some list buttons (clear a whole list; swap both lists).
- **Other mouse buttons** (expert) — for example right-click for color or middle-click to reset on compact divider buttons.

{{tr:settings.ui_mode_beginner}} keeps those jobs on separate buttons instead of stacking them.

:::figure{side=block height=44}
![Long-press on a list button]({{img:ui.buttons.long_press}})
List button — short click vs long-press.
:::

### Find a control by name {#find-action}

Open the palette with `Ctrl+Shift+P` ({{tr:menu.find_action}}), type part of the label, and run the action or press `Ctrl+Enter` to open {{tr:action.palette.learn_more}} when the row has a help topic.
