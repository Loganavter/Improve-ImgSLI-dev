## Video Editor

A live {{tr:workspace.session_types.image_compare}} session, recorded as work happens, with timeline trim and encode to video or GIF. Stills stay on [Export](help://export).

### Session recording {#recording}

- **Transport** — {{tr:image_compare.action.record}} (`R`), {{tr:image_compare.action.pause_recording}}, then stop from the same buttons. Record and pause sit on the toolbar in every density except minimal.
- **Recorded work** — canvas activity over time (zoom/pan, divider, magnifier, loaded images, related settings) — not a screen recording.
- **Capture rate** — [Settings](help://settings#image_compare) ({{tr:settings.recording_fps}}).

### Editor opening {#open-editor}

After the recording stops, {{tr:image_compare.action.video_editor}} (`Ctrl+E`) scrubs frames, edits the range, and exports. Editor actions in {{tr:menu.find_action}} open this topic.

### Timeline editing {#timeline}

- **Scrubbing** — a drag of the time cursor.
- **Range marking** — `Shift`+drag marks a span; edge handles and the middle of the selection move independently; {{tr:image_compare.button.trim_to_selection}} keeps only that selection.
- **Range deletion** — `Delete` / `Backspace` remove the selected range.
- **Playback** — `Space`; undo / redo — `Ctrl+Z` / `Ctrl+Y`.

:::figure{side=block width=100%}
![Video timeline]({{img:workspace.image_compare.video.timeline}})
{{tr:image_compare.action.video_editor}} — timeline.
:::

### Recorded content {#tracks}

The editor lists each recorded tool on its own timeline row (splitter, magnifier, canvas view, and similar), so the moment each tool changed during the session stays visible. Result changes come from trimming or deleting ranges on the [timeline](help://video#timeline) and from undo or redo.

### Preview quality {#preview-quality}

{{tr:video.preview_quality}} only lowers the in-editor preview for responsiveness. Final encode quality is unchanged.

- **{{tr:video.preview_quality_full}}** — sharpest preview; heaviest on the machine; the default.
- **{{tr:video.preview_quality_balanced}}** — lighter trade-off for most sessions.
- **{{tr:video.preview_quality_performance}}** — lighter preview when scrubbing feels slow.
- **{{tr:video.preview_quality_draft}}** — fastest preview; least detail.

### Video or GIF export {#export-encode}

- **Framing** — resolution (lock aspect as needed), FPS (not above recording FPS), fit vs crop; optional fill color for empty edges.
- **Codec** — container and codec on the standard tab; hardware encoders appear only when the system exposes them.
- **Quality** — CRF/CQ or bitrate and related presets.
- **Path** — output file; favorite directory buttons reuse the last preferred folder.
- **Progress** — stoppable; the log reports encoder messages.

:::figure{side=block width=280}
![Video export panel]({{img:workspace.image_compare.video.export_encode}})
{{tr:image_compare.action.video_editor}} — export.
:::

### {{tr:video.manual_cli}} {#manual-cli}

When the standard tab is not enough, {{tr:video.manual_cli}} passes custom FFmpeg output arguments.

### Next topics {#next-topics}

Still images: [Export](help://export). Diff and magnifier during recording match the live canvas — [Comparison](help://comparison) and [Magnifier](help://magnifier).
