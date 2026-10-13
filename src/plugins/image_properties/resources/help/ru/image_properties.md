## Свойства изображения

Метаданные файла и контекст в приложении для одного загруженного изображения. Диалог открывается поверх сессии и ничего в ней не меняет.

:::figure{side=block width=280}
![Диалог свойств изображения]({{img:platform.image_properties.open}})
{{tr:image_properties.title}}.
:::

### Открытие диалога {#open}

Пункт {{tr:image_compare.action.context_properties}} в контекстном меню изображения открывает {{tr:image_properties.title}} для этого изображения. Пункт {{tr:recent.action_properties}} в контекстном меню недавних проектов открывает его для этого проекта.

### Разделы {#sections}

Строки сгруппированы так:

- {{tr:image_properties.section_file}} — имя, расположение и параметры файла
- {{tr:image_properties.section_image}} — основные параметры изображения
- {{tr:image_properties.section_app}} — как сессия размещает это изображение (ниже)
- {{tr:image_properties.section_metadata}} — поля камеры / EXIF, если файл их отдаёт

Диалог скрывает пустые строки и разделы без значений; ошибку чтения файла он помечает как {{tr:image_properties.read_error}}.

### Контекст в приложении {#in-app}

{{tr:image_properties.section_app}} показывает, как сессия размещает изображение (сторона, позиция, оценка — в зависимости от типа сессии). Эти строки — состояние сессии, а не файл.

### Закрытие {#close}

{{tr:image_properties.close}} закрывает диалог. {{tr:image_properties.copy_all}} копирует все видимые строки в буфер обмена; часть страницы копируется из выделения через {{tr:action.context_copy}} (или сначала {{tr:action.context_select_all}}).
