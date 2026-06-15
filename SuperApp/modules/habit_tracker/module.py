from __future__ import annotations

from typing import TYPE_CHECKING

from core.base_module import BaseModule

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class HabitTrackerModule(BaseModule):
    """Модуль ежедневного трекинга привычек."""

    def __init__(self) -> None:
        self._widget: QWidget | None = None

    @property
    def module_id(self) -> str:
        return "habit_tracker"

    @property
    def display_name(self) -> str:
        return "Привычки"

    @property
    def icon_path(self) -> str:
        return ""

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        from modules.habit_tracker.ui.habit_view import HabitView
        self._widget = HabitView(parent)
        return self._widget

    def on_activated(self) -> None:
        if self._widget is not None:
            self._widget.refresh()  # type: ignore[attr-defined]