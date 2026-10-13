## Files and Projects

Loading images into sessions and portable project files.

### Loading images {#loading-images}

- **Files** — one or more files through {{tr:menu.find_action}} or the tab's own add buttons.
- **Drag-and-drop** — a drop into the window lands in the active session — where exactly, see the tab's help: [Comparison](help://comparison), [Magnifier](help://magnifier).
- **Paste** (`Ctrl+V`) — clipboard image; where it lands, see the tab's help.

:::figure{side=block width=280}
![Paste direction overlay]({{img:platform.file_project.paste_overlay}})
`Ctrl+V` — paste direction overlay.
:::

### Lists {#lists}

Lists belong to their session — [Lists and Panels](help://ui.lists_flyouts). Each session has its own tab — [Tabs](help://tabs).

### Projects {#projects}

- **Opening** — `Ctrl+Shift+O` or {{tr:menu.find_action}} opens a `.imgsli` file. Opening a project names the active tab after the file.
- **Saving** — `Shift+S` writes the current file; when no file exists yet, **Save As** opens instead.
- **Save As** — `Ctrl+Shift+S`. Suggests the renamed tab title, otherwise {{tr:menu.project_untitled}}.
- **Portable package** — a single file bundles the session layout, session settings, and embedded copies of the images.
- **Missing sources on save** — if a listed path no longer exists, the project still saves; that image is omitted and a warning lists it.
- **App preferences** — theme, language, and hotkeys stay in application settings; they are not part of the project file.

### Windows file association {#windows-file-association}

On Windows, double-clicking an `.imgsli` file opens it in the app. If the system asks which application to use, one pick of Improve ImgSLI applies.
