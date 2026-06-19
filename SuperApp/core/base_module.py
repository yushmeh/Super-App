from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class BaseModule(ABC):
    """
    Контракт для всех утилит SuperApp.
    """

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Уникальный идентификатор (snake_case). Ключ в реестре и QStackedWidget."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Название, отображаемое в навигационной панели."""
        ...

    @property
    @abstractmethod
    def icon_path(self) -> str:
        """Путь к иконке. Вернуть '' если иконки нет."""
        ...

    @abstractmethod
    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        """Фабричный метод. Создаёт и возвращает главный виджет модуля."""
        ...

    def on_activated(self) -> None:
        """Хук: вызывается при каждом переключении НА модуль."""

    def on_deactivated(self) -> None:
        """Хук: вызывается при переключении С модуля."""

    def __repr__(self) -> str:
        return f"<Module id={self.module_id!r} name={self.display_name!r}>"