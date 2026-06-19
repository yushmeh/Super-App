from __future__ import annotations

from typing import TYPE_CHECKING

from core.base_module import BaseModule

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class BudgetTrackerModule(BaseModule):
    """Модуль управления бюджетом, расходами и целями накоплений."""

    def __init__(self) -> None:
        self._widget: QWidget | None = None

    @property
    def module_id(self) -> str:
        return "budget_tracker"

    @property
    def display_name(self) -> str:
        return "Бюджет"

    @property
    def icon_path(self) -> str:
        return ""

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        from modules.budget_tracker.ui.budget_view import BudgetView
        self._widget = BudgetView(parent)
        return self._widget

    def on_activated(self) -> None:
        if self._widget is not None:
            self._widget.refresh()  # type: ignore[attr-defined]