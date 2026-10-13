## Buttons and Controls

The toolbar sits at the top and holds the action buttons of the active tab.

:::figure{side=block height=107}
![Session toolbar]({{img:ui.buttons.toolbar}})
Toolbar above the canvas.
:::

### The toolbar {#toolbar}

Each tab decides which buttons its toolbar shows.

### Interface modes {#ui-modes}

Layout density follows the interface mode — see the active tab's help for details: [Comparison](help://comparison#toolbar), [Magnifier](help://magnifier#toolbar), [Layouts](help://mc_layouts#toolbar). The mode changes under [Settings → Appearance](help://settings#interface).

### Several actions on one button {#multi-action}

Depending on the interface mode, one button can respond to several gestures:

- **Short click** — primary action or toggle.
- **Scroll** — a value adjusted without opening a dialog.
- **Long-press** — stronger variant on some buttons.
- **Other mouse buttons** — extra variants in the densest mode.

:::figure{side=block height=44}
![Long-press on a list button]({{img:ui.buttons.long_press}})
List button — short click vs long-press.
:::

### Action lookup by name {#find-action}

The palette opens with `Ctrl+Shift+P` ({{tr:menu.find_action}}); a typed label fragment narrows the list. An action runs from its row, and `Ctrl+Enter` opens {{tr:action.palette.learn_more}} when the row has a help topic.
