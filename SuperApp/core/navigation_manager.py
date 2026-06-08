"""
core/navigation_manager.py
==========================
Менеджер навигации SuperApp. Паттерн «Посредник» (Mediator).
Связывает ModuleRegistry с QStackedWidget.
Переключение между модулями мгновенное — виджеты не пересоздаются.
"""
from __future__ import annotations

from PyQt6.QtWidgets import QStackedWidget, QWidget

from core.base_module import BaseModule
from core.module_registry import ModuleRegistry


class NavigationManager:
    """
    Управляет QStackedWidget: создаёт виджеты модулей и переключает их.
    Вызывает хуки on_activated / on_deactivated при каждом переходе.
    """

    def __init__(self, registry: ModuleRegistry) -> None:
        self._registry = registry
        self._stack = QStackedWidget()
        self._index_map: dict[str, int] = {}
        self._current_module: BaseModule | None = None

        for module in registry:
            self._add_module_to_stack(module)

    def _add_module_to_stack(self, module: BaseModule) -> None:
        widget: QWidget = module.create_widget(parent=None)
        idx = self._stack.addWidget(widget)
        self._index_map[module.module_id] = idx

    @property
    def stack_widget(self) -> QStackedWidget:
        """QStackedWidget для встраивания в MainWindow."""
        return self._stack

    def navigate_to(self, module_id: str) -> bool:
        """
        Переключается на модуль с указанным ID.
        Возвращает True при успехе, False если модуль не найден.
        """
        if module_id not in self._index_map:
            return False

        if self._current_module is not None:
            self._current_module.on_deactivated()

        self._stack.setCurrentIndex(self._index_map[module_id])

        new_module = self._registry.get(module_id)
        if new_module is not None:
            self._current_module = new_module
            new_module.on_activated()

        return True

    def current_module_id(self) -> str | None:
        """ID текущего активного модуля."""
        return self._current_module.module_id if self._current_module else None