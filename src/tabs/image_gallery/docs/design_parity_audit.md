# Image Gallery — Design Parity Audit

Status: `Audited → фиксы применены` (см. «Статус правок» внизу) (свежий прогон против макетов `design/ui-mockup-v2-triage.svg`,
`design/ui-mockup-v3-clean-review.svg`, `design/ui-mockup-v4-quicklook.svg` +
[design.md](design.md); живая геометрия сверена по UI-layout dump окна).
Предыдущий аудит (`plan_design_parity.md`) удалён как устаревший: часть его
пунктов уже реализована (HUD инстанцирован, формула `redundant`, хедеры
`SERIES i · hub · n VARIANTS`, marquee hit-test по `card.geometry()`),
часть — сформулирована неверно.

Верификация после правок: `./launcher.sh test tests/contracts -q` +
`env QT_QPA_PLATFORM=offscreen pytest -q src/tabs/image_gallery/tests`.

## Что уже соответствует макетам (не трогать)

- Selection HUD: `SelectionHudController` создан и подключён
  (`widget.py:252`), в дампе окна присутствует `BaseFlyout:GallerySelectionHud`
  с clear/analyze/find_similar/carry; супресс в S3 через `FlyoutManager` +
  `set_suppressed` (`ui/clean_review.py:206-248`).
- Stats strip: формула `redundant = total - series_cnt - ungrouped_cnt`
  (`widget.py:730`), live `Clean rejected (n)` (`stats_strip.py:79-89`),
  mode chip `FIDELITY MODE · source: …` (`stats_strip.py:91-107`).
- S1: спиннер + `n/N` в тулбаре (`toolbar.py:221-252`) и empty-state
  (`ui/states.py:195-237`), `✓ triage complete` по завершении
  (`toolbar.py:254-272`).
- Card: rejected = overlay dim-wash (substrate @0.62 ≈ effect 0.38) +
  strike-through, без toolkit-бейджа `✕` и без `QGraphicsOpacityEffect`
  (эффект диммил всё поддерево включая hover-капсулу — она выцветала;
  wash красит только саму карточку, дети crisp), карточка остаётся
  кликабельной; badge-приоритет overlay-пилюль `AI tie-break… > ★ BEST > #N`,
  rejected подавляет overlay-пилюлю (`ui/card/visuals.py`,
  `ui/card/painters.py:_gallery_rejected_dim`).
- Series grid: кластеры ≥2 с коллапс-хедерами `SERIES {i} · {hub} · {n} VARIANTS ▾`,
  UNGROUPED-хвост (`ui/grid_view.py:338-398`).
- S3: `TopLevelInWindowOverlay(close_on_escape=True)`, provenance-строка
  `SERIES N · hub (cnt)` с хаб-резолвером (`ui/clean_review.py:281-327`),
  per-item/per-series/Restore all, `Move N to _rejected/` (primary), move-only
  `clean_rejected` + тост `ToastAction("Undo")` 10 s (`clean_review.py:564-624`).
- S4: двухпанельный overlay, source inset оверлеем в левом нижнем углу
  превью (`ui/quick_look.py:479-520, 681-712`), dual-bar restored↔invented,
  Esc/←→, dbl-click (`ui/quick_look_hooks.py:251`).
- Клавиатура Space/B/Enter/стрелки/Esc (`use_cases/triage_ui.py:103-236`).
- Marquee hit-test по живой геометрии карточек с fixed-grid fallback
  (`ui/marquee.py:58-142`).

## Расхождения — S2 (mockup v2)

| # | Макет | Реализация | Где |
|---|---|---|---|
| S2-1 | Три точки качества окрашены индивидуально (green/mild/flagged per artifact) | `_dots_for_item` считает per-dot цвета, но рендерится вся строка `● ● ●` первым цветом (`color=first_color`); посчитанные цвета хранятся мёртвым грузом в `card._gallery_dot_colors` | `ui/card.py:355-371` |
| S2-2 | Hover: светлее фон + 3px акцентное подчёркивание снизу карточки | Только IconActionFlyout-капсула; underline и фон hover не рисуются | `ui/card.py:36-56` |
| S2-3 | Unreadable-карточка: `!` плейсхолдер + красное `unreadable — excluded from triage` | Нет specialized error-плейсхолдера; `analysis_error` рисуется обычной строкой без стиля/исключения из триажа | `ui/card.py:316-354` |
| S2-4 | Хедер серии: 3px синяя полоса слева (UNGROUPED — серая) | Ghost Button только с текстом, полосы нет | `ui/grid_view.py:400-446` |
| S2-5 | `Clean rejected (n)` — акцентный stroke, текст #7fc4ff | Все три кнопки strip одинаковый `variant="surface"` | `ui/stats_strip.py:46-59` |
| S2-6 | `33 redundant` — акцентный цвет | Весь stats label одним цветом | `ui/stats_strip.py:72-77` |
| S2-7 | `✓ triage complete` зелёный (`#3fbf5f`) | Label цветом по умолчанию | `ui/toolbar.py:134-140` |
| S2-8 | View-switch: icon-pair grid/list (иконки) | Пустой `Button(toggle=True)` без иконок; переключение — заглушка (layout не меняется) | `ui/toolbar.py:95-110`, `widget.py:321-331` |
| S2-9 | Бейдж `AI tie-break…` — синий stroke, текст #7fc4ff | Серый filled бейдж | `ui/card.py:787-792` |
| S2-10 | Open Folder с синей иконкой папки | Plain surface Button без иконки | `ui/toolbar.py:56-64` |
| S2-11 | Индикатор триажа по центру тулбара, view-toggle прижат вправо | Stretch в конце: спиннер/индикатор уходят правее view-switch (подтверждено дампом: view_switch x=920 при ширине 1650) | `ui/toolbar.py:112-143` |
| S2-12 | Цвета только через theme tokens | Хардкод `#D93025/#3fbf5f/#e8b64c/#c0392b/#0096ff` в card.py | `ui/card.py:108-110, 781-814, 1199-1207` |

## Расхождения — S3 (mockup v3)

| # | Макет | Реализация | Где |
|---|---|---|---|
| S3-1 | Сабтайтл `N files will be moved to <folder>/_rejected/ — nothing is deleted, Undo available for 10 s.` | Отсутствует (только title) — ключевое safety-обещание не показано до движения | `ui/clean_review.py:127-130` |
| S3-2 | Тумбы 150×100, toolkit-виджет | QLabel 100×70 с текстовым плейсхолдером `IMG` | `ui/clean_review.py:454-468` |
| S3-3 | Тайл `+N more` с пунктиром (scrollable strip) | Нет — все ячейки подряд | `ui/clean_review.py:366-531` |
| S3-4 | `↩ Restore` | `Restore` (без стрелки; мелочь) | `ui/clean_review.py:490` |

## Расхождения — S4 (mockup v4)

| # | Макет | Реализация | Где |
|---|---|---|---|
| S4-1 | Source inset: янтарная рамка + подпись `SOURCE · name · 960×540` (с размерами) | Рамка не рисуется (попытка через palette), в подписи только имя | `ui/quick_look.py:504-516, 917-918` |
| S4-2 | Значение banding `mild · sky region` — специфика banding | `"mild · sky region"` захардкожено для ЛЮБОГО артефакта уровня mild («Halo: mild · sky region» — враньё) | `ui/quick_look.py:1329` |
| S4-3 | Banding-гистограмма — визуализация данных детектора (comb spikes) | Статичные декоративные высоты `[40,44,38,32]`, данные не используются | `ui/quick_look.py:265-332` |
| S4-4 | Репорт показывает значимые строки (5 readouts) | Все 7 артефактов всегда, включая clean — шум | `ui/quick_look.py:1300-1346` |
| S4-5 | Сублайн SSIM `#2 scores 0.91 · rejected tail ≤ 0.83` | Нет | `ui/quick_look.py:1131` |
| S4-6 | Camera mode: sharpness, exposure+clipping, noise, WB shift | Noise estimate и WB shift отсутствуют | `ui/quick_look.py:1176-1198` |
| S4-7 | Стрип: SOURCE gold border / viewing blue border / rejected dim 0.4 | `setProperty("border_color", …)` — painter pipeline свойство игнорирует; rejected-тумбы не приглушаются | `ui/quick_look.py:1455-1481` |
| S4-8 | Bottom bar: Compare → акцентная, ✕ Reject красная, Set as source янтарная | Все `variant="surface"` | `ui/quick_look.py:650-668` |
| S4-9 | FIDELITY MODE chip — accent-тинтованный | Plain Label | `ui/quick_look.py:423-429` |
| S4-10 | Цвета через theme tokens | QPalette + хардкод-цвета в `_BarWidget`, `_DualRestoredInventedBar`, обеих гистограммах | `ui/quick_look.py:82-96, 174-213, 279-361` |

## Toolkit hygiene (design.md «Toolkit rules», план A1-A6)

- Raw `QVBoxLayout/QHBoxLayout` при построении toolkit-виджетов — по всей
  вкладке (`widget.py:89`, `ui/toolbar.py:51`, `ui/stats_strip.py:36`,
  `ui/clean_review.py:123-181`, `ui/quick_look.py` — весь файл). Долг,
  зафиксированный ещё в старом плане; менять точечно вместе с пунками выше.
- `QLabel` вместо toolkit Label/painter — `clean_review.py:454`,
  `quick_look.py:468, 499, 531` (превью/тумбы).
- setStyleSheet нигде не используется — OK.

## Рекомендованный порядок правок

1. Дешёвые визуальные фиксы: S2-4…S2-11, S3-1, S3-4, S4-1, S4-8, S4-9.
2. Функциональные: S2-1 (per-dot цвета), S2-3 (unreadable card), S4-2
   (баг-текст), S4-4 (фильтр clean-строк), S4-6, S4-7.
3. Данные детекторов в визуализации: S4-3 (+ прокинуть
   `services/artifacts.py` выходы в `models.GalleryItem.artifacts`, если ещё
   не прокинуты).
4. Toolkit hygiene: перевод инлетов на painter pipeline (S4-10, S3-2, QLabel).
5. Заглушки: S2-8 (list view) — оставить до отдельной задачи (выполнено 2026-09-27: режим внутри GalleryGridView, билдеры ui/list_card.py).


## Статус правок (прогон 2026-08-27)

Исправлено оркестрацией 4 агентов (A1 toolbar/stats_strip, A2 card, A3 clean_review, A4 quick_look):

- S2-1..S2-7, S2-9..S2-11 — done (A1/A2). S2-8 — визуально done (icon-pair grid/horizontal_split,
  `list.svg` в toolkit нет), поведение остаётся grid-only заглушкой.
- S2-12 — done для card.py (`_token_color` + ThemeManager.try_get_color, fallback hex).
- S3-1..S3-4 — done (A3): сабтайтл с folder/N/Undo 10s, тумбы toolkit Label 150×100,
  кэп 8 ячеек + тайл «+N more», «↩ Restore».
- S4-1..S4-9 — done (A4): янтарная рамка inset через paintEvent, размеры в подписи,
  «mild · sky region» только у banding, чистые артефакты скрыты, SSIM-сублайн,
  camera noise + WB shift, strip borders через `Button.set_border_color` + dim 0.4,
  bottom bar акцент/красный/янтарный через painter API, chip accent.
- S4-10 — частично: новый код на токенах; старые `_BarWidget`/`_DualRestoredInventedBar`/
  гистограммы на QPalette оставлены (отдельная задача).
- Дополнительно: `variant="primary"` (deprecated) в clean_review заменён на surface +
  accent background.

**Заметки по toolkit (для будущих задач):**
- Нет токенов `success/warning/danger` в палитрах toolkit и `themes.json` — везде
  fallback hex; предложить промоутить токены в toolkit.
- Нет `list.svg` иконки; нет dashed-border API; нет per-run color spans в `ButtonRow`.

Верификация: `env QT_QPA_PLATFORM=offscreen pytest -q src/tabs/image_gallery/tests` —
76 passed. `tests/contracts` не собирается из-за ПРЕДСУЩЕСТВУЮЩИХ конфликт-маркеров
merge в `src/__main__.py`, `src/ui/main_window/startup.py`,
`src/ui/canvas_infra/scene/pass_contract.py` и i18n JSON — вне скоупа вкладки.

## Статус правок — parity close-out 2026-09-22/23 ([plan](plan_mockup_parity_2026-09-22.md))

Ветка `int/gallery-parity-2026-09`, 4 волны, merged без конфликтов.
Полный сьют на merged tree: **1893 passed, 66 skipped**
(baseline 1870 + 23 новых регрессионных теста).

- **Волна A (triage-core):** P0-1 `_series_of` читает `series` на owner и
  `owner.state` (порядок `_triage_series, triage_series, _series, series`);
  P0-2 live `set_rejected_count` из `_refresh_owner_grid`; strip Keep best →
  `keep_best_of_series` (rejects rest — spec mockup); stale "(stub)" убраны.
- **Волна B (fidelity+S4):** P0-3 новый `services/fidelity_metrics.py`
  (`compute/apply/run_fidelity_sync`, identity fail-closed по `item.path`);
  P0-4 маркер `frac = 0.5 − clamp(hf)·0.5` (+0.18 → 0.41);
  P0-5 multi-compare merge вместо clobber; P0-6 set-source переключает режим
  (chip FIDELITY); P0-8 убран фейковый "sky region"; P0-9 гистограммы 36→56px;
  S4-визуал (meta-порядок, `Series 1 · hub`, chip-pill, dividers, min 1040×620,
  зелёные значения, vs-#2 fallback из локальных метрик).
- **Волна C (S2):** P0-7 импорт `Qt` в toolbar; fill-chip view-toggle;
  AI tie-break — in-thumbnail pill; хедеры uppercase + токены
  (`rg '#9a9a9a' grid_view.py` → 0); rank `#dfdfdf`; 6 raw-hex → токены;
  легенда dots в design.md исправлена на artifact-каталог (код dots не тронут).
  Честные partial: letter-spacing нет в ButtonRow API; "!" остался текстом
  региона; тинт иконок капсулы требует поддержки toolkit.
- **Волна D (S3+veil):** provenance `from: ` под filmstrip (svg:100);
  горизонтальный скролл past cap 8; тост `Moved N files`, `success=True`, без MB;
  primary-комментарий приведён к коду. **P0-10 вердикт: `TopLevelInWindowOverlay`
  НЕ диммит (нет paintEvent) — app-side veil 0.45 (`DIM_VEIL_ALPHA=115`) в scope
  галереи; правка toolkit — отдельная задача в другом репо.**
