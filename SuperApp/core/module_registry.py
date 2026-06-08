"""
core/module_registry.py
=======================
Реестр модулей SuperApp.

Хранит все зарегистрированные модули и предоставляет
доступ к ним по ID. Ядро и UI работают только через реестр,
не импортируя конкретные модули напрямую.
"""
from __future__ import annotations

from typing import Iterator

from core.base_module import BaseModule


class ModuleRegistry:
    """
    Центральный реестр плагинов/модулей.

    Использование:
        registry = ModuleRegistry()
        registry.register(CurrencyTrackerModule())
        modules = registry.all_modules()
    """

    def __init__(self) -> None:
        # Упорядоченный словарь: id → модуль
        self._modules: dict[str, BaseModule] = {}

    def register(self, module: BaseModule) -> None:
        """
        Регистрирует модуль. Вызывается один раз при старте приложения.
        Выбрасывает ValueError при дублировании ID.
        """
        mid = module.module_id
        if mid in self._modules:
            raise ValueError(
                f"Модуль с ID '{mid}' уже зарегистрирован. "
                f"Каждый module_id должен быть уникальным."
            )
        self._modules[mid] = module

    def get(self, module_id: str) -> BaseModule | None:
        """Возвращает модуль по ID или None если не найден."""
        return self._modules.get(module_id)

    def all_modules(self) -> list[BaseModule]:
        """Возвращает список всех зарегистрированных модулей в порядке регистрации."""
        return list(self._modules.values())

    def __iter__(self) -> Iterator[BaseModule]:
        return iter(self._modules.values())

    def __len__(self) -> int:
        return len(self._modules)