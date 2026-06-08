"""
core/base_module.py
===================
Контракт (абстрактный базовый класс) для всех модулей SuperApp.

Каждая утилита ДОЛЖНА реализовать этот интерфейс.
Ядро работает только через этот контракт — конкретных классов не знает.
Это реализация паттернов «Шаблонный метод» + «Плагин».
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget


class BaseModule(ABC):
    """
    Абстрактный базовый класс для всех модулей (утилит) SuperApp.

    Контракт:
    - module_id:      уникальный строковый идентификатор (snake_case)
    - display_name:   человекочитаемое название для навигационной панели
    - icon_path:      путь к SVG/PNG иконке (может быть пустой строкой)
    - create_widget:  фабричный метод, возвращающий главный QWidget модуля

    Жизненный цикл:
    1. ModuleRegistry.register(module_instance) — регистрация при старте
    2. NavigationManager запрашивает create_widget() при первом переходе
    3. QWidget кэшируется и показывается при навигации
    """

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Уникальный ID, используется как ключ в реестре и QStackedWidget."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Название, отображаемое в боковой навигации."""
        ...

    @property
    @abstractmethod
    def icon_path(self) -> str:
        """Путь к иконке модуля. Вернуть '' если иконки нет."""
        ...

    @abstractmethod
    def create_widget(self, parent: QWidget | None = None) -> QWidget:
        """
        Фабричный метод: создаёт и возвращает главный QWidget модуля.
        Вызывается ОДИН РАЗ при первом открытии.
        """
        ...

    def on_activated(self) -> None:
        """
        Хук: вызывается каждый раз при переключении НА этот модуль.
        Переопределяйте для обновления данных, старта таймеров и т.д.
        По умолчанию — ничего не делает.
        """

    def on_deactivated(self) -> None:
        """
        Хук: вызывается при переключении С этого модуля.
        Переопределяйте для остановки фоновых задач, сохранения состояния.
        По умолчанию — ничего не делает.
        """

    def __repr__(self) -> str:
        return f"<Module id={self.module_id!r} name={self.display_name!r}>"