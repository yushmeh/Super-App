"""
main.py
=======
Точка входа SuperApp.

Ответственности этого файла:
1. Создать QApplication и применить глобальную тему
2. Зарегистрировать все модули в ModuleRegistry
3. Создать NavigationManager и MainWindow
4. Запустить event loop

Добавление нового модуля:
    1. Создайте папку modules/my_module/ с классом MyModule(BaseModule)
    2. Добавьте строку:  registry.register(MyModule())
    Больше ничего менять не нужно.
"""
from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from core.module_registry import ModuleRegistry
from core.navigation_manager import NavigationManager
from modules.currency_tracker.module import CurrencyTrackerModule
from ui.components.nav_sidebar import NavSidebar
from ui.components.placeholder_screen import PlaceholderScreen
from ui.themes.scifi_dark import GLOBAL_QSS

# Заглушки для слотов 2-5 — минимальные реализации BaseModule
from core.base_module import BaseModule


def _make_placeholder_module(slot_index: int, name: str) -> BaseModule:
    """Фабрика заглушек: создаёт анонимный BaseModule для нереализованных слотов."""

    class _PlaceholderModule(BaseModule):
        @property
        def module_id(self) -> str:
            return f"placeholder_{slot_index}"

        @property
        def display_name(self) -> str:
            return name

        @property
        def icon_path(self) -> str:
            return ""

        def create_widget(self, parent: QWidget | None = None) -> QWidget:
            return PlaceholderScreen(slot_index - 1, parent)

    return _PlaceholderModule()


class MainWindow(QMainWindow):
    """
    Главное окно SuperApp.

    Компоновка:
        [NavSidebar | ContentArea (QStackedWidget)]

    NavSidebar испускает сигнал → NavigationManager переключает стек.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        nav_manager: NavigationManager,
    ) -> None:
        super().__init__()
        self._registry = registry
        self._nav_manager = nav_manager

        self.setWindowTitle("SUPERAPP — CONTROL PANEL")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        self._build_ui()
        self._navigate_to_default()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("ContentArea")
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Боковая навигация
        self._sidebar = NavSidebar(self._registry.all_modules())
        self._sidebar.module_selected.connect(self._on_module_selected)
        layout.addWidget(self._sidebar)

        # Область контента
        layout.addWidget(self._nav_manager.stack_widget, stretch=1)

    def _navigate_to_default(self) -> None:
        modules = self._registry.all_modules()
        if modules:
            first_id = modules[0].module_id
            self._nav_manager.navigate_to(first_id)
            self._sidebar.set_active(first_id)

    def _on_module_selected(self, module_id: str) -> None:
        self._nav_manager.navigate_to(module_id)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SuperApp")
    app.setOrganizationName("SuperApp Labs")

    # Применяем глобальную Sci-Fi Dark тему
    app.setStyleSheet(GLOBAL_QSS)

    # Регистрация модулей
    registry = ModuleRegistry()
    registry.register(CurrencyTrackerModule())                         # Слот 1: активный
    registry.register(_make_placeholder_module(2, "Портфолио"))        # Слот 2
    registry.register(_make_placeholder_module(3, "Мониторинг"))       # Слот 3
    registry.register(_make_placeholder_module(4, "Крипто"))           # Слот 4
    registry.register(_make_placeholder_module(5, "Аналитика"))        # Слот 5

    # Создание менеджера навигации
    nav_manager = NavigationManager(registry)

    # Главное окно
    window = MainWindow(registry, nav_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()