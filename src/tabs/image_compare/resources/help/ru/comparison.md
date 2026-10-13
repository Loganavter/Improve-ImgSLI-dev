## Сравнение

Два изображения на всём холсте: подвижный разделитель, подписи имён, каналы и режимы разницы — без лупы. Живой холст, экспорт кадров и запись видео выглядят одинаково.

### Линия раздела {#split-line}

При выключенной лупе тяните разделитель по паре.

- **Ориентация** — {{tr:image_compare.action.divider_orientation}} переключает горизонталь / вертикаль.
- **Ширина** — колесо над {{tr:image_compare.action.divider_width}}.
- **Цвет** — {{tr:image_compare.action.divider_color}}.
- **Видимость** (`D`) — {{tr:image_compare.action.divider_visible}} показывает или скрывает линию.
- **Комбинированный** — {{tr:image_compare.action.divider_combined}} собирает ориентацию, ширину и цвет (скролл / ПКМ / СКМ); жесты в подсказке контрола.

:::figure{side=block width=280}
![Линия раздела]({{img:workspace.image_compare.comparison.split_line}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.divider}}.
:::

### Скролл по картинкам {#scroll-images}

- **Колесо на холсте** — шагает список на стороне под курсором (слева от вертикального раздела / выше горизонтального = сторона 1; другая половина = сторона 2).
- **`Shift` + колесо** — оба списка сразу.
- **Превью одной стороны** — колесо всегда шагает видимую сторону.
- **Колесо на списке** — шагает эту сторону без открытия панели; см. [Списки и панели](help://ui.lists_flyouts#scroll-lists).
- **Поменять** (`X`) — короткий клик меняет текущую пару; удержание — оба списка.

### Подписи {#labels-and-metrics}

- **Показать имена** (`N`) — {{tr:image_compare.action.file_names}}; при включении могут попасть в экспорт.
- **Зум** — подписи скрываются при приближении и возвращаются на полном кадре.
- **Настройки текста** — {{tr:image_compare.action.text_settings}} открывает панель: размер, начертание, непрозрачность, цвета, фон и размещение.

### Метрики {#metrics}

- **{{tr:image_compare.ui.psnr}} / {{tr:image_compare.ui.ssim}}** — по умолчанию выкл.; авторасчёт — в [Настройках](help://settings#image_compare) в разделе {{tr:workspace.session_types.image_compare}}.

### Действия контекстного меню {#context-menu-actions}

- **Свойства** — [Свойства изображения](help://image_properties) из контекстного меню строки списка (метаданные и сторона / рейтинг).
- **Переместить** — пункт контекстного меню на холсте или в списке: превью следует за указателем. Клик по другой вкладке или холсту размещает его, как при дублировании или вставке. `Esc` или ПКМ — отмена.

### Режимы канала {#channel-modes}

{{tr:image_compare.action.channel_mode}} (`C`) переключает RGB, R, G, B и яркость, чтобы смотреть один канал, не уходя с холста.

### Режимы разницы {#difference-modes}

{{tr:image_compare.action.diff_mode}} (`H` циклически) подчёркивает отличия пары:

:::figure{side=block width=280}
![Режим разницы]({{img:workspace.image_compare.comparison.difference_modes}})
{{tr:image_compare.action.diff_mode}}.
:::

- **{{tr:image_compare.action.diff_highlight}}** — зоны изменений на живой паре
- **{{tr:image_compare.action.diff_grayscale}}** — обесцвечивание разницы яркости
- **{{tr:image_compare.action.diff_edges}}** — разница по краям
- **{{tr:image_compare.action.diff_ssim}}** — карта структурного сходства, когда метрики доступны

Режимы разницы сочетаются с каналами. Для локального осмотра — [Лупа](help://magnifier).
