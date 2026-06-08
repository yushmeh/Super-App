# 🛸 SUPERAPP — Модульная десктопная платформа утилит

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.7+-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://www.riverbankcomputing.com/software/pyqt/)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%203--Tier-00D4FF?style=for-the-badge)](https://en.wikipedia.org/wiki/Multitier_architecture)
[![Style](https://img.shields.io/badge/UI-Sci--Fi%20Dark%20Mode-cyan?style=for-the-badge)](https://developer.mozilla.org/en-US/docs/Web/CSS)

**SuperApp** — десктопная платформа-оболочка для независимых утилит, построенная на **PyQt6 (Python 3.11+)** с использованием паттерна **Plugin/Module** и архитектуры **Clean Architecture (3-Tier)**.

Интерфейс выполнен в стиле **Sci-Fi Dark Mode**: тёмный фон, неоновые акценты, монопространственный шрифт.

---

## 📋 Содержание

- [🚀 Ключевые особенности](#-ключевые-особенности)
- [📂 Структура проекта](#-структура-проекта)
- [🧩 Реализованные и планируемые модули](#-реализованные-и-планируемые-модули)
- [🏗 Архитектура](#-архитектура)
- [🖥 Выбор UI-фреймворка](#-выбор-ui-фреймворка)
- [🔌 Добавление нового модуля](#-добавление-нового-модуля)
- [🛠 Запуск](#-запуск)
- [👤 Автор](#-автор)

---

## 🚀 Ключевые особенности

### 🏗 Архитектура
- **Clean Architecture / 3-Tier** — строгое разделение на слои данных, бизнес-логики и представления внутри каждого модуля.
- **Plugin/Module паттерн** — ядро не знает о конкретных утилитах. Добавление нового модуля не затрагивает ни одной строки кода ядра.
- **QStackedWidget навигация** — мгновенное переключение между модулями без пересоздания виджетов.

### ⚡ Асинхронность
- Сетевые запросы выполняются в отдельном `QThread` (воркер-паттерн).
- Результаты передаются в UI-поток через сигналы Qt — интерфейс никогда не блокируется.

### 🎨 UI
- Глобальная QSS-тема в стиле Sci-Fi Dark: тёмный фон (`#0A0E17`), неоновый синий (`#00D4FF`), оранжевый акцент (`#FF6B35`).
- Экраны-заглушки с анимацией и уникальными кодовыми именами для незавершённых модулей.

---

## 📂 Структура проекта

```text
superapp/
├── core/
│   ├── base_module.py          # Абстрактный контракт для всех модулей
│   ├── module_registry.py      # Реестр зарегистрированных модулей
│   └── navigation_manager.py  # Управление QStackedWidget
│
├── modules/
│   └── currency_tracker/       # ✅ Утилита 1: Трекер валют
│       ├── api/
│       │   └── cbr_client.py   # Async HTTP-клиент ЦБ РФ
│       ├── logic/
│       │   └── data_processor.py  # Парсинг XML, валидация
│       ├── ui/
│       │   └── currency_view.py   # Виджет с графиком
│       └── module.py           # Точка входа: реализация BaseModule
│
├── ui/
│   ├── themes/
│   │   └── scifi_dark.py       # Цветовая палитра и глобальный QSS
│   └── components/
│       ├── nav_sidebar.py      # Боковое навигационное меню
│       └── placeholder_screen.py  # Экран-заглушка для будущих модулей
│
├── main.py                     # Точка входа: регистрация модулей, MainWindow
├── requirements.txt
└── README.md
```

---

## 🧩 Реализованные и планируемые модули

### ✅ Утилита 1 — Трекер валют (`currency_tracker`)
Отслеживание курсов валют по данным Центрального Банка РФ.
- Текущий курс для USD, EUR, CNY, GBP, JPY, CHF, HKD, TRY.
- История курса за произвольный диапазон дат с выбором через календарь.
- Интерактивный график pyqtgraph: линия тренда с заливкой, точки на узлах (для коротких периодов), автомасштаб.
- Изменение курса за период: ▲/▼ с цветовой индикацией.

---

### 🔜 Утилита 2 — Портфолио (`portfolio_tracker`) *(в разработке)*
Персональный трекер инвестиционного портфеля.
- Ручное добавление активов: акции, облигации, ETF, валюта.
- Расчёт текущей стоимости портфеля и P&L в реальном времени.
- Круговая диаграмма распределения активов по классам.
- Экспорт отчёта в CSV/Excel.

### 🔜 Утилита 3 — Мониторинг системы (`system_monitor`) *(в разработке)*
Реал-тайм дашборд состояния локальной машины.
- Графики CPU, RAM, дисков и сетевого трафика (обновление каждые 2 секунды).
- История нагрузки за сессию.
- Алерты при превышении порогов.
- Реализация на базе `psutil`.

### 🔜 Утилита 4 — Крипто-трекер (`crypto_tracker`) *(в разработке)*
Мониторинг котировок криптовалют через публичный API CoinGecko.
- Топ-20 монет по капитализации с сортировкой.
- История цены за 7 / 30 / 90 дней с графиком.
- Конвертер: крипта → RUB / USD / EUR.
- Индикатор Fear & Greed Index.

### 🔜 Утилита 5 — Аналитика (`data_analytics`) *(в разработке)*
Интерактивный инструмент для анализа пользовательских данных.
- Загрузка CSV/XLSX файлов с автодетектом кодировки.
- Базовая статистика: среднее, медиана, стандартное отклонение, выбросы.
- Построение графиков: линия, гистограмма, scatter-plot.
- Экспорт результатов анализа.

---

## 🏗 Архитектура

### 3-Tier внутри каждого модуля

```
┌─────────────────────────────────────┐
│  UI Layer  (modules/*/ui/)          │  QWidget, отображение, события
├─────────────────────────────────────┤
│  Logic Layer  (modules/*/logic/)    │  валидация, парсинг, вычисления
├─────────────────────────────────────┤
│  Data Layer  (modules/*/api/)       │  HTTP, файлы, кэш
└─────────────────────────────────────┘
```

Зависимости идут **только сверху вниз**: UI → Logic → Data. Обратных зависимостей нет.

### Схема ядра

```
ModuleRegistry ──register()──► BaseModule (ABC)
       │                            ▲
       ▼                            │ реализует
NavigationManager              modules/*/module.py
       │
       ▼
  QStackedWidget
       │
  ┌────┴────┐
  │  slot 0 │ CurrencyTrackerModule.create_widget()
  │  slot 1 │ PlaceholderModule.create_widget()
  │  ...    │
  └─────────┘
```

---

## 🖥 Выбор UI-фреймворка

### PyQt6 vs CustomTkinter

| Критерий | PyQt6 | CustomTkinter |
|---|---|---|
| **Расширяемость** | ✅ Полный виджет-стек, кастомные `QWidget` | ⚠️ Ограниченный набор |
| **Темизация** | ✅ QSS (CSS-like), `QPalette`, `QPainter` | ⚠️ Только встроенные темы |
| **Асинхронность** | ✅ `QThread`, сигналы/слоты — потокобезопасно | ❌ Нет встроенной поддержки |
| **Графики** | ✅ pyqtgraph — нативный Qt, 60fps | ❌ Только через Matplotlib |
| **Зрелость** | ✅ 25+ лет, Qt Creator, Anki, VLC | ⚠️ Молодой проект |
| **Кастомизация** | ✅ Полный контроль через subclassing | ❌ Сложно |

**Вывод**: PyQt6 — единственный выбор для платформы с требованиями к кастомной теме, асинхронным воркерам и встроенным высокопроизводительным графикам.

---

## 🔌 Добавление нового модуля

Чтобы добавить утилиту, **ядро менять не нужно**. Достаточно трёх шагов:

### Шаг 1: Создайте папку модуля

```
modules/
└── my_tool/
    ├── __init__.py
    ├── module.py       ← обязательный файл
    ├── api/
    ├── logic/
    └── ui/
```

### Шаг 2: Реализуйте `BaseModule` в `module.py`

```python
from core.base_module import BaseModule
from PyQt6.QtWidgets import QWidget

class MyToolModule(BaseModule):

    @property
    def module_id(self) -> str:
        return "my_tool"

    @property
    def display_name(self) -> str:
        return "Мой инструмент"

    @property
    def icon_path(self) -> str:
        return ""

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        from .ui.main_view import MyToolView
        return MyToolView(parent)
```

### Шаг 3: Зарегистрируйте в `main.py`

```python
from modules.my_tool.module import MyToolModule

registry.register(MyToolModule())
```

Модуль автоматически появится в боковом меню.

---

## 🛠 Запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Запустить приложение
python main.py
```

**Требования**: Python 3.11+

---

## 👤 Автор

[@yushmeh](https://github.com/yushmeh)
