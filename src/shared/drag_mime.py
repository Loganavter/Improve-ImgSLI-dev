"""Wire mimes for in-window image drags (tab content → workspace tab strip).

One definition, three consumers:

* producers — tab content surfaces that start a path-carrying ``QDrag``
  (gallery cards: ``tabs/image_gallery/ui/grid_view/drag_source.py``; Multi
  Compare slots: ``tabs/multi_compare/canvas/interaction.py``);
* consumer — the host strip router (``ui/main_window/tab_strip_drop.py``),
  which may not import a tab module (platform isolation, contracts
  ``test_platform_isolation`` / ``test_ui_tab_sandbox``).

``WORKSPACE_TAB_PATHS_MIME`` payload = newline-separated ``file://`` URLs,
mirrored into ``QMimeData.setUrls()`` so a drop target that only reads URLs
(``ui.main_window.tab_strip_drop.parse_card_paths``) still sees the files.
Copy semantics: files stay on disk, the source tab keeps its own copy — the
drop only starts the target tab's pending-insert UX (same flow as Duplicate).
"""

from __future__ import annotations

#: Mime carried by a drag that hands image paths from tab content to another
#: workspace tab. The strip claims it on enter/move/drop; the payload alone
#: decides what is delivered.
WORKSPACE_TAB_PATHS_MIME = "application/x-imgsli-workspace-tab-paths"
