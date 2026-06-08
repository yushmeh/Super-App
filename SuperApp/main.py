"""
main.py
=======
Точка входа SuperApp.
Регистрирует модули, создаёт NavigationManager и запускает главное окно.

Добавление нового модуля:
    1. Создайте папку modules/my_module/ с классом MyModule(BaseModule)
    2. Добавьте строку: registry.register(MyModule())
"""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QWidget

from core.base_module import BaseModule
from core.module_registry import ModuleRegistry
from core.navigation_manager import NavigationManager
from modules.currency_tracker.module import CurrencyTrackerModule
from ui.components.nav_sidebar import NavSidebar
from ui.components.placeholder_screen import PlaceholderScreen
from ui.themes.scifi_dark import GLOBAL_QSS


def _make_placeholder_module(slot_index: int, name: str) -> BaseModule:
    """Фабрика заглушек для слотов с ещё не реализованными модулями."""

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

    Компоновка: [NavSidebar | QStackedWidget]
    NavSidebar испускает сигнал → NavigationManager переключает стек.
    """

    def __init__(self, registry: ModuleRegistry, nav_manager: NavigationManager) -> None:
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

        self._sidebar = NavSidebar(self._registry.all_modules())
        self._sidebar.module_selected.connect(self._nav_manager.navigate_to)
        self._sidebar.module_selected.connect(self._sidebar.set_active)
        layout.addWidget(self._sidebar)
        layout.addWidget(self._nav_manager.stack_widget, stretch=1)

    def _navigate_to_default(self) -> None:
        modules = self._registry.all_modules()
        if modules:
            first_id = modules[0].module_id
            self._nav_manager.navigate_to(first_id)
            self._sidebar.set_active(first_id)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("SuperApp")
    app.setOrganizationName("SuperApp Labs")
    app.setStyleSheet(GLOBAL_QSS)

    registry = ModuleRegistry()
    registry.register(CurrencyTrackerModule())
    registry.register(_make_placeholder_module(2, "Портфолио"))
    registry.register(_make_placeholder_module(3, "Мониторинг"))
    registry.register(_make_placeholder_module(4, "Крипто"))
    registry.register(_make_placeholder_module(5, "Аналитика"))

    nav_manager = NavigationManager(registry)
    window = MainWindow(registry, nav_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()