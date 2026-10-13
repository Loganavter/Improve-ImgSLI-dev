## Свойства изображения

Метаданные файла и контекст в приложении для одного загруженного изображения. Диалог висит над сессией и ничего в ней не меняет.

:::figure{side=block width=280}
![Диалог свойств изображения]({{img:platform.image_properties.open}})
{{tr:image_properties.title}}.
:::

### Открыть диалог {#open}

Пункт {{tr:image_compare.action.context_properties}} в контекстном меню списка или слота открывает {{tr:image_properties.title}} для этого изображения. Пункт {{tr:recent.action_properties}} в контекстном меню недавних проектов открывает его для этого проекта.

### Разделы {#sections}

Строки сгруппированы так:

- {{tr:image_properties.section_file}} — имя, путь, расширение, размер на диске, формат, время изменения
- {{tr:image_properties.section_image}} — размер в пикселях, мегапиксели, пропорции, ориентация, каналы, DPI и режим / профиль цвета, если есть
- {{tr:image_properties.section_app}} — как приложение разместило изображение в текущей сессии (ниже)
- {{tr:image_properties.section_metadata}} — поля камеры / EXIF, если файл их отдаёт

Пустые строки пропускаются, а раздел без значений скрывается целиком; ошибка чтения файла показывается как {{tr:image_properties.read_error}}.

### Контекст в приложении {#in-app}

{{tr:image_properties.section_app}} зависит от того, откуда открыт диалог. Запись {{tr:workspace.session_types.image_compare}} несёт {{tr:image_properties.side}} (лево / право) и {{tr:image_properties.rating}}. Ячейка {{tr:workspace.session_types.multi_compare}} несёт {{tr:image_properties.position}}. Недавний проект несёт вместо этого свой учёт — даты, последнее открытие, типы сессий. Эти строки описывают состояние сессии, а не файл на диске.

### Закрытие {#close}

{{tr:image_properties.close}} закрывает диалог. {{tr:image_properties.copy_all}} копирует все видимые строки в буфер обмена; чтобы скопировать часть страницы, выделите её и используйте {{tr:action.context_copy}} (или сначала {{tr:action.context_select_all}}).
