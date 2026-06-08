# SuperApp

> Модульная десктопная платформа для утилит — расширяемая, производительная, с Sci-Fi Dark интерфейсом.

---

## Концепция

**SuperApp** — это не монолит, а *оболочка для инструментов*. Каждая утилита (трекер валют, мониторинг сервера, калькулятор, и т.д.) живёт в отдельном модуле в папке `modules/` и не знает ни о других модулях, ни о ядре — только о своём контракте (`BaseModule`). Ядро (`core/`) лишь регистрирует и отображает модули, не завися от их содержимого.

Архитектурный принцип: **Open/Closed** — открыто для расширения, закрыто для модификации ядра.

---

## Выбор UI-фреймворка: PyQt6

### Почему PyQt6, а не CustomTkinter?

| Критерий | PyQt6 | CustomTkinter |
|---|---|---|
| **Расширяемость** | ✅ Полноценный виджет-стек, QSS-стили, кастомные QWidget | ⚠️ Ограниченный набор виджетов |
| **Темизация** | ✅ QSS (CSS-like), глобальные палитры, QPainter | ⚠️ Только встроенные темы |
| **Асинхронность** | ✅ QThread, QRunnable, сигналы/слоты — потокобезопасно | ❌ Нет встроенной поддержки |
| **Графики** | ✅ PyQtGraph (нативная интеграция, GPU-ускорение) | ❌ Только через Matplotlib |
| **Продакшн-зрелость** | ✅ 25+ лет, используется в Qt Creator, Anki, VLC | ⚠️ Молодой проект |
| **Кастомные компоненты** | ✅ Полный контроль через subclassing | ❌ Сложно |

**Вывод**: PyQt6 — единственный разумный выбор для продакшн-платформы с требованиями к темизации, асинхронности и графикам.

---

## Структура проекта

```
superapp/
│
├── core/                          # Ядро: абстракции, навигация, реестр модулей
│   ├── __init__.py
│   ├── base_module.py             # Абстрактный класс BaseModule (контракт плагина)
│   ├── module_registry.py         # Реестр: автообнаружение и хранение модулей
│   └── navigation_manager.py      # Менеджер навигации (QStackedWidget)
│
├── modules/                       # Папка утилит — каждая независима
│   └── currency_tracker/          # Утилита 1: Трекер валют
│       ├── api/                   # Слой данных: HTTP-клиент CBR
│       │   ├── __init__.py
│       │   └── cbr_client.py
│       ├── logic/                 # Бизнес-логика: парсинг, валидация
│       │   ├── __init__.py
│       │   └── data_processor.py
│       ├── ui/                    # UI-слой модуля
│       │   ├── __init__.py
│       │   └── currency_view.py
│       ├── __init__.py
│       └── module.py              # Точка входа: реализация BaseModule
│
├── ui/                            # Общие UI-компоненты и темы
│   ├── themes/
│   │   ├── __init__.py
│   │   └── scifi_dark.py          # Палитра, QSS, константы темы
│   └── components/
│       ├── __init__.py
│       ├── nav_sidebar.py         # Боковое навигационное меню
│       └── placeholder_screen.py  # Экран-заглушка для будущих модулей
│
├── main.py                        # Точка входа приложения
├── requirements.txt
└── README.md
```

---

## Добавление нового модуля (паттерн Plugin/Module)

Чтобы добавить новую утилиту, **ядро менять не нужно**. Всего 3 шага:

### Шаг 1: Создайте папку модуля

```
modules/
└── my_new_tool/
    ├── __init__.py
    ├── module.py          ← обязательный файл
    ├── api/
    ├── logic/
    └── ui/
```

### Шаг 2: Реализуйте `BaseModule` в `module.py`

```python
# modules/my_new_tool/module.py
from core.base_module import BaseModule
from PyQt6.QtWidgets import QWidget

class MyNewToolModule(BaseModule):

    @property
    def module_id(self) -> str:
        return "my_new_tool"

    @property
    def display_name(self) -> str:
        return "Мой новый инструмент"

    @property
    def icon_path(self) -> str:
        return "assets/my_icon.svg"  # или ""

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        # Верните главный виджет вашего модуля
        from .ui.main_view import MyToolView
        return MyToolView(parent)
```

### Шаг 3: Зарегистрируйте в `main.py`

```python
from modules.my_new_tool.module import MyNewToolModule

registry.register(MyNewToolModule())
```

Всё. Модуль автоматически появится в боковом меню и будет доступен через навигацию.

---

## Архитектура трёх уровней (3-Tier)

```
┌─────────────────────────────────────┐
│  UI Layer (PyQt6 Widgets)           │  ← только отображение, события
│  modules/*/ui/                      │
├─────────────────────────────────────┤
│  Business Logic Layer               │  ← валидация, преобразование данных
│  modules/*/logic/                   │
├─────────────────────────────────────┤
│  Data Layer (API / Storage)         │  ← HTTP-запросы, кэш, файлы
│  modules/*/api/                     │
└─────────────────────────────────────┘
```

Зависимости идут **только сверху вниз**: UI → Logic → Data. Обратных зависимостей нет.

---

## Запуск

```bash
pip install -r requirements.txt
python main.py
```

**Требования**: Python 3.11+ (код совместим с 3.11–3.14).

---

## Технический стек

- **UI**: PyQt6 6.7+
- **Графики**: pyqtgraph (нативный Qt, 60fps)
- **HTTP**: httpx (async-клиент)
- **Парсинг XML**: lxml
- **Типизация**: strict typing с `from __future__ import annotations`
