# Plan: gallery light-theme contrast revision

Status: `Plan` (orchestrated; waves via separate clones).
Area: `src/tabs/image_gallery/` + `src/resources/themes.json` (light section only).
Base branch: `main` of Improve-ImgSLI (integration branch `int/gallery-light` cut on launch).

## Goal / non-goals

Goal: белая тема галереи доводится до читаемости тёмной — карточки, hover, stats-плашка,
разделители и QuickLook различаются визуально, все поверхности перекрашиваются на флип темы.
Контрастные нормы: body-текст ≥4.5:1, крупный/компоненты/бордеры ≥3:1
(копия харнеса `tests/test_contrast.py` из sli-ui-toolkit).

Non-goals: тёмная палитра не трогается (только сверка hex с мокапами);
новые виджеты/фичи галереи; правки toolkit-репозитория (только чтение
`DESIGN_LANGUAGE.md`); тёмные fallback-литералы вне галереи.

## Why (разведка 2026-09-23, 4 сабагента)

- Все 3 мокапа (`design/ui-mockup-v{2,3,4}-*.svg`) — тёмные. `dark` в `themes.json`
  совпадает с ними hex-в-hex; `light` выдумана без мокапа и без нормы контраста.
- Топ-3 плоских мест light: `gallery.card.background #f5f5f5` == `Window #f5f5f5` (1:1);
  `gallery.card.hover #f0f0f0` vs card ~1.05:1 (== `surface.list`);
  `separator.color #e5e5e5` на `#fff` ~1.2:1 + `stats.background #e1e1e1` vs card ~1.15:1.
- Код читает `gallery.*` токены, но все fallback-ветки тёмные
  (`(56,56,56)`==`#383838`, `#333`, `#0096FF`; комменты `ui/card.py:38`,
  `ui/card/hover.py:19` врут что токен не зарегистрирован).
- `ThemedWidget|theme_changed|on_theme_changed` — 0 хитов в `image_gallery/`:
  подписки нет, флип темы не перекрашивает.
- Запрещённый `setPalette+AutoFillBackground` (THEMING.md warm-up баг):
  `quick_look/bars.py:73,77,134,161,199`, `helpers.py:193,264`,
  `histograms.py:50,81,110`, `grid_view.py:462`.
- Чистый хардкод: `toolbar.py:31,83,85,90,92`, `grid_view.py:458,460`,
  `artifacts.py:121`.
- Тесты parity есть (`tests/runtime/test_card_parity.py:296,321`,
  `test_toolbar_parity.py:117`), flip-теста light↔dark нет.

## Shared seam interface (frozen, все волны обязаны)

- Токены читаются только через `try_resolve_theme_color(manager, "<token>")`
  (app-контракт; bare `get_color` вне theme-infra запрещён).
- Fallback-цепочки светлые, парами light/dark рядом в коде:
  `gallery.card.background → surface.list → surface.background → #ffffff (light) / #383838 (dark)`;
  `gallery.accent.bar → accent → #0078D4 (light) / #0096FF (dark)`.
  Никаких голых `#383838`/`#333`/`(56,56,56)` как дефолта.
- Перекрас только через `ThemedWidget.on_theme_changed()` + `paintEvent.fillRect`
  (запрет `setPalette+setAutoFillBackground` для фонов; запрет `setStyleSheet`
  на toolkit-виджетах — painter pipeline владеет выводом).
- Иконки — lazy `AppIcon`, не eager `QIcon` (иначе замирают на старой теме).
- Каждая волна в `DONE.md` пишет `INTERFACE:` — какие токены/хелперы добавила/меняла
  с сигнатурами; `none` только если `git diff main...<branch> -G "^def |^class "` пуст.

## Ownership (волны, disjoint файлы, max 4 writers)

| Wave | Owner | owns_files | Scope |
|---|---|---|---|
| W1 palette | worker-w1 | `src/resources/themes.json` (light-секция `gallery.*`, `separator.color` + смежные `Window/surface.*` только light) | Развести card/Window/surface, hover-степ ≥1.3:1, separator/stats ≥3:1; прогнать contrast-харнес |
| W2 card+stats | worker-w2 | `src/tabs/image_gallery/ui/card/**`, `ui/card.py`, `ui/stats_strip.py`, `ui/grid_view.py` | Светлые fallback-цепочки, ThemedWidget-подписка, токенизация точки секции `grid_view:458,460`, правка врущих комментов |
| W3 toolbar+quicklook | worker-w3 | `src/tabs/image_gallery/ui/toolbar.py`, `ui/quick_look/**` | Токенизация toolbar-хардкода, `setPalette`→`paintEvent` в bars/helpers/histograms, severity `artifacts.py:121` через `_token_*` |
| W4 tests+docs | worker-w4 | `src/tabs/image_gallery/tests/**`, `src/tabs/image_gallery/docs/design.md` (контраст-норма, 1 секция) | Flip-тест light↔dark, contrast-тест галерейных пар, норма светлой темы в design.md |

`base_branch` всех воркеров: `int/gallery-light`. `catalog.yaml` не трогается
(кодовая задача, не knowledge-plane). `dark`-секция `themes.json` — read-only для всех.

## Phases

1. **W1 palette**: новые light-значения gallery-карт/hover/stats/separator;
   verify: contrast-харнес зелёный (пары из §Why ≥3:1, текст ≥4.5:1),
   `git diff` только light-секция.
2. **W2/W3 виджеты** (параллельно после W1-значений, читают новые токены):
   verify: флип темы вручную через `--ui-inspector` + offscreen-тест перекраса;
   `grep -rn "56,56,56\|#383838\|#333333\|setPalette" ui/` пуст (кроме комментов-плана).
3. **W4 тесты+дока**: verify: `env QT_QPA_PLATFORM=offscreen pytest -q src/tabs/image_gallery/tests`
   + `./launcher.sh test tests/contracts -q` зелёные; `file_meta --write-registry`
   если размеры файлов менялись.
4. **Интеграция** (супервизор): merge волн в `int/gallery-light` по одной,
   `merge-tree` без `<<<<<<<`, контракты+галерея-тесты на merged tree,
   затем PR в `main`. `auto:`-коммиты дропнуть (`rebase -i main`).

Per-phase verify — та же команда для всех:
`PYTHONDONTWRITEBYTECODE=1 env QT_QPA_PLATFORM=offscreen pytest -q src/tabs/image_gallery/tests -p no:cacheprovider`
плюс `./launcher.sh test tests/contracts -q`.

## Risks / guards

- Daemon-autopush (`*-autopush.timer`) коммитит каждые 15 мин в `backup/autopush` —
  на время мёржей `systemctl --user stop *autopush.timer`, после — start.
- Никогда два райтера в одном чекауте: один воркер = один клон `agent-clone.sh` + ветка
  `agent/<task-id>/work`. Worktree/shared-stash запрещены.
- Timebox: S (W1,W4) 60 мин, M (W2,W3) 120 мин. Heartbeats: pre-flight ≤15 мин,
  baseline green ≤30 мин, первый scoped edit ≤45 мин, первый push ≤60 мин.
  Каждый wait-slice: `agent-spin.sh` + `scripts/worker_progress.sh`, худший вердикт действует.
  Второй подряд пропуск milestone → kill + salvage + split/supervisor-takeover.
- Попытки на infra-смерти: 2 мёртвые, 3-я последняя — дальше split/takeover.
- Каждый wait-slice заканчивается user-visible checkpoint (elapsed, состояние,
  последнее реальное evidence, ETA). Молчаливых multi-slice ожиданий нет.
- `sli-ui-toolkit` — editable (`requirements-gui.txt: -e ../sli-ui-toolkit`),
  но волны его НЕ правят (read-only reference).

## Claimed-vs-real close-out

Верификатор читает файлы, не доверяет `git diff` (autopush мог замести);
открывает каждый claimed файл на cited line; прогоняет named suites
(contracts минимум); resync registries. Комменты/проза плана недоверены —
только исполняемые statements. Green subset ≠ integration green:
прогон на merged `int/gallery-light` целиком.

## Progress log

- 2026-09-23: разведка (4 research-сабагента) — причины неконтраста зафиксированы выше.
- 2026-09-23: план создан, ветка интеграции `int/gallery-light` — следующий шаг (супервизор).
- 2026-09-23: W1 (палитра `f52aab82`), W2 (карточки `df4f8f22`), W3 (тулбар+QL `c18d0a66`),
  W4 (тесты+Rule A `29480856`) влиты; claimed-vs-real по диффам + сьютам на merged tree.
- 2026-09-23: RESCOPE субстрата (супервизор, напрямую): `Window`/`surface.background`/
  `separator.color` возвращены к доэпическим значениям — серый субстрат живёт только
  в новом `gallery.grid.background` (light `#cecece` / dark `#2b2b2b`), грид красится
  через `set_fill_color`. Причина: токен `Window` → `QPalette.Window`, серость текла
  во все `autoFillBackground`-виджеты аппы; `separator.color` вообще не читается галереей.
