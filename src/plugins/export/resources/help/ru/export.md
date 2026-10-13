## Экспорт

Экспорт текущего холста как статичного изображения. Захват сессии и кодирование видео — отдельная тема: [Видеоредактор](help://video).

:::figure{side=block width=630}
![Диалог экспорта]({{img:workspace.image_compare.export.dialog}})
{{tr:image_compare.action.breadcrumb.toolbar}} → {{tr:image_compare.action.breadcrumb.export}}.
:::

### Сохранение кадра {#saving-an-image}

Диалог открывается кнопкой {{tr:image_compare.action.save}} на панели инструментов или через {{tr:menu.find_action}}.

- **Путь** — каталог и имя файла.
- **Формат** — формат из списка.
- **Превью** — собранный результат на предпросмотре до записи.

### Разрешение и качество {#resolution-and-quality}

- **Размер** — размер кадра.
- **Качество** — {{tr:label.quality}} показывается, когда применимо к формату.
- **PNG** — уровень сжатия и {{tr:export.optimize_png}}.
- **Заливка** — {{tr:export.fill_background}} закрашивает пустые поля вокруг изображения; {{tr:export.background_color}} задаёт цвет. Где закрашивать нечего, опция недоступна.

### Метаданные и избранное {#metadata-and-favorites}

- **Метаданные** — {{tr:export.include_metadata}} остаются включёнными, пока не выключены; поле комментария скрывается вместе с ними. {{tr:export.remember_by_default}} сохраняет текст комментария для следующего экспорта.
- **Избранное** — {{tr:misc.set_as_favorite}} закрепляет текущий каталог; {{tr:tooltip.use_favorite}} возвращает его.
- **Подписи** — если включены {{tr:image_compare.action.file_names}}, имена попадают в кадр как состояние сессии, а не данные файла.

### Быстрое сохранение {#quick-save}

- **`Ctrl+S`** — {{tr:image_compare.action.quick_save}} повторяет последние настройки экспорта без открытия диалога.
