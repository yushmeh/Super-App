"""
core/navigation_manager.py
==========================
Менеджер навигации SuperApp.

Управляет QStackedWidget — контейнером, в котором каждый модуль
занимает один «слот». Переключение мгновенное без пересоздания виджетов.

Паттерн: «Посредник» (Mediator) между боковым меню и областью контента.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QStackedWidget, QWidget

from core.base_module import BaseModule
from core.module_registry import ModuleRegistry


class NavigationManager:
    """
    Связывает ModuleRegistry с QStackedWidget.

    - При первом переходе лениво (lazy) создаёт виджет модуля
    - Вызывает хуки on_activated / on_deactivated
    - Отдаёт стек наружу — MainWindow встраивает его в лейаут
    """

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry
        self._stack = QStackedWidget()
        # Словарь id → индекс в стеке
        self._index_map: dict[str, int] = {}
        # Текущий активный модуль (для хука deactivated)
        self._current_module: BaseModule | None = None

        # Предварительно добавляем все модули в стек (виджеты создаются лениво)
        for module in registry:
            self._add_module_to_stack(module)

    def _add_module_to_stack(self, module: BaseModule) -> None:
        """Создаёт виджет модуля и добавляет в стек."""
        widget: QWidget = module.create_widget(parent=None)
        idx = self._stack.addWidget(widget)
        self._index_map[module.module_id] = idx

    @property
    def stack_widget(self) -> QStackedWidget:
        """Главный стек-виджет для встраивания в MainWindow."""
        return self._stack

    def navigate_to(self, module_id: str) -> bool:
        """
        Переключается на модуль с указанным ID.

        Возвращает True при успехе, False если модуль не найден.
        Вызывает on_deactivated для предыдущего и on_activated для нового.
        """
        if module_id not in self._index_map:
            return False

        # Деактивируем текущий
        if self._current_module is not None:
            self._current_module.on_deactivated()

        # Активируем новый
        idx = self._index_map[module_id]
        self._stack.setCurrentIndex(idx)

        new_module = self._registry.get(module_id)
        if new_module is not None:
            self._current_module = new_module
            new_module.on_activated()

        return True

    def current_module_id(self) -> str | None:
        """Возвращает ID текущего активного модуля."""
        if self._current_module is None:
            return None
        return self._current_module.module_id