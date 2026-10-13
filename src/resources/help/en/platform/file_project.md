## Files and Projects

Load images into session lists, paste from the clipboard, and open or save portable project files that bundle session layout, compare settings, and copies of the source images.

### Loading images {#loading-images}

- **Add files** — use the side add buttons (or {{tr:menu.find_action}}) to pick one or more files.
- **Drag-and-drop** — a drop into the window lands in the list on the side under the cursor.
- **Paste** (`Ctrl+V`) — clipboard image; the direction overlay appears, a click on an arrow picks the side, `Esc` cancels.

:::figure{side=block width=280}
![Paste direction overlay]({{img:platform.file_project.paste_overlay}})
`Ctrl+V` — paste direction overlay.
:::

### Lists {#lists}

Lists belong to their session — [Lists and Panels](help://ui.lists_flyouts). Each session has its own tab — [Tabs](help://tabs).

### Projects {#projects}

- **Open** — `Ctrl+Shift+O`, or {{tr:menu.find_action}}, opens a `.imgsli` file from the File menu. Opening a project names the active tab after the file. The project restores workspace sessions, compare settings, and embedded image copies.
- **Save** — `Shift+S` writes the current file; when no file exists yet, **Save As** opens instead. Saving also retargets the file basename when the tab was renamed.
- **Save As** — `Ctrl+Shift+S`. Suggests a renamed tab title when the active tab is custom, otherwise {{tr:menu.project_untitled}}.
- **Portable package** — a single file bundles the session layout, compare settings, and embedded copies of the images.
- **Missing sources on save** — if a listed path no longer exists, the project still saves; that image is omitted and a warning lists it.
- **App preferences** — theme, language, and hotkeys stay in application settings; they are not part of the project file.

### Windows file association {#windows-file-association}

On Windows, the installer associates `.imgsli` with Improve ImgSLI, so double-clicking a project opens it and the file shows the application's document icon. Frozen builds also register the association on startup.

If Properties still shows "Choose application", pick Improve ImgSLI once, or run the app with `--register-file-types` to register the association again.
