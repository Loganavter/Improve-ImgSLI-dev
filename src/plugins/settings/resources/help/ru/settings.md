## Настройки

Поведение приложения в одном диалоге: встроенные страницы плюс секции вкладок рабочей области (анализ сравнения, AI-данные галереи). Секции вкладок видны всегда, независимо от активной сессии.

### Открыть настройки {#open-settings}

- **Меню** — {{tr:menu.settings}} (`Ctrl+,`).
- **Панель** — кнопка настроек.
- **{{tr:menu.find_action}}** — `Ctrl+Shift+P` и имя страницы ({{tr:settings.general}}, {{tr:settings.appearance}}, {{tr:settings.keyboard}}, …).
- **{{tr:action.palette.learn_more}}** — у действия настроек открывает подходящий якорь, если тег задан.
- **{{tr:common.ok}}** — применяет текущие значения, диалог остаётся открытым.
- **{{tr:common.cancel}}** — закрывает диалог.
- **Esc** — никогда не закрывает диалог настроек; очищает поиск, если он активен.

### Поиск в настройках {#search}

Поле поиска над списком разделов: совпадения идут по одной строке на раздел, независимо от глубины совпадения (имя элемента, название группы, любой язык). Выбор строки открывает раздел с пульсацией найденных опций. `Esc` очищает поиск и возвращает полный список. Список разделов растягивается.

### Общие {#general}

- **{{tr:label.language}}** — en / ru / zh / pt_BR.
- **{{tr:label.theme}}** — auto / light / dark.
- **{{tr:settings.system_notifications}}** — переключатель уведомлений ОС.
- **{{tr:settings.enable_debug_logging}}** — подробные логи для отладки.

### Внешний вид {#interface}

- **{{tr:settings.ui_mode}}** — радиокнопки {{tr:settings.ui_mode_beginner}} / {{tr:settings.ui_mode_advanced}} / {{tr:settings.ui_mode_expert}}; по умолчанию новичок, сюда же попадает выбор первого запуска.
- **{{tr:settings.ui_font}}** — встроенный, системный или свой шрифт.
- **{{tr:settings.ui_scale}}** — масштаб интерфейса.
- **Лимиты** — например максимальная длина отображаемого имени.

### Производительность {#performance}

- **{{tr:settings.render_backend_label}}** — доступные бэкенды зависят от платформы; смена применяется при следующем запуске.

### {{tr:workspace.session_types.image_compare}} {#image_compare}

Параметры сравнения, доступны всегда: сначала сглаживание, затем захват и метрики:

- **{{tr:settings.zoom_interpolation}}** — качество ресемплинга зума холста.
- **{{tr:settings.optimize_magnifier_movement}}** — плавное движение лупы, метод интерполяции — в той же строке.
- **{{tr:settings.optimize_laser_smoothing}}** — сглаживание шлейфа лазера, метод интерполяции — в той же строке.
- **{{tr:settings.magnifier_intersection_highlight}}** — подсветка пересечения линз.
- **{{tr:settings.magnifier_auto_color_new_instances}}** — разные цвета новых линз.
- **{{tr:image_compare.settings.recording_fps}}** — частота захвата для [Видеоредактора](help://video).
- **{{tr:settings.autocrop_black_borders_on_load}}** — обрезка чёрных полей при загрузке.
- **Авто {{tr:ui.psnr}} / {{tr:ui.ssim}}** — автоматический подсчёт метрик, по умолчанию выключен.

### {{tr:image_gallery.settings.ai_title}} {#image-gallery-ai}

Запросы ИИ в [Галерее изображений](help://gallery_triage) используют настройки ниже. Для запроса нужны включённый ИИ-переключатель, API-ключ и модель — одного ключа недостаточно.

- **{{tr:image_gallery.settings.enable_ai}}** — включает или выключает функции ИИ.
- **{{tr:image_gallery.settings.base_url}}** — адрес ИИ-сервиса.
- **{{tr:image_gallery.settings.api_key}}** — ключ для этого сервиса. {{tr:image_gallery.settings.api_key_warning}}
- **{{tr:image_gallery.settings.model_name}}** — модель для запросов.

### Клавиатура {#keyboard}

- **Переназначение** — ярлыки по владельцам: platform / {{tr:workspace.session_types.image_compare}} / {{tr:workspace.session_types.multi_compare}}.
- **Сброс** — одного ярлыка или всех.
- **Фиксированные** — `WASD` и `Space` на холсте не ремапятся — см. [Горячие клавиши](help://hotkeys).
