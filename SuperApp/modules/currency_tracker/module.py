"""
modules/currency_tracker/module.py
===================================
Точка входа модуля «Трекер валют».
Реализует контракт BaseModule и регистрируется в ModuleRegistry при старте.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from core.base_module import BaseModule

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class CurrencyTrackerModule(BaseModule):
    """Модуль отслеживания курсов валют ЦБ РФ."""

    def __init__(self) -> None:
        self._widget: QWidget | None = None

    @property
    def module_id(self) -> str:
        return "currency_tracker"

    @property
    def display_name(self) -> str:
        return "Трекер валют"

    @property
    def icon_path(self) -> str:
        return ""

    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        from modules.currency_tracker.ui.currency_view import CurrencyView
        self._widget = CurrencyView(parent)
        return self._widget

    def on_activated(self) -> None:
        """При переходе на модуль — автозагрузка текущего курса."""
        if self._widget is not None:
            self._widget.refresh()  # type: ignore[attr-defined]