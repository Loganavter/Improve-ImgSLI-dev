## Canvas Navigation

Movement inside the compare canvas: cursor-centered zoom, middle-button pan, wheel stepping, `Space` full-side preview.

:::figure{side=block width=280}
![Canvas zoom and pan]({{img:ui.canvas_navigation.zoom}})
{{tr:workspace.session_types.image_compare}} → canvas.
:::

### Zoom and pan {#zoom}

- **Zoom** — `Ctrl` + wheel over the canvas.
- **Step frames** — plain wheel steps the images on the side under the cursor; see [Comparison](help://comparison#scroll-images).
- **Pan** — middle mouse button + drag.

### Quick side preview {#quick-side-preview}

Compare-canvas gestures (see [Comparison](help://comparison)):

- **Full side** — hold `Space` and click: `LMB` shows the left image full-canvas, `RMB` the right.
- **Switch** — while `Space` is still held, click the other button for the other side.
- **Release** — release `Space` to return to the normal split.
- **Inside the combined lens** — `Space` + `Shift` + click in the lens previews that side inside the lens (see [Magnifier](help://magnifier)).

### While zoomed {#zoom-side-effects}

- **Filename labels** — hide only when zoomed past `100%` in the normal split view; they stay on while zoomed out and in side preview, and return on fit.
- **Split line** — fractional position (0–1); the fraction holds while zoom changes.
- **Render quality** — interpolation in [Settings](help://settings#image_compare); backend switch under [Settings → Performance](help://settings#performance).
