"""
core/module_registry.py
=======================
Центральный реестр модулей SuperApp.
Хранит зарегистрированные модули и предоставляет доступ по ID.
"""
from __future__ import annotations

from typing import Iterator

from core.base_module import BaseModule


class ModuleRegistry:
    """
    Реестр плагинов/модулей.

    Использование:
        registry = ModuleRegistry()
        registry.register(CurrencyTrackerModule())
        modules = registry.all_modules()
    """

    def __init__(self) -> None:
        self._modules: dict[str, BaseModule] = {}

    def register(self, module: BaseModule) -> None:
        """Регистрирует модуль. Выбрасывает ValueError при дублировании ID."""
        mid = module.module_id
        if mid in self._modules:
            raise ValueError(f"Модуль с ID '{mid}' уже зарегистрирован.")
        self._modules[mid] = module

    def get(self, module_id: str) -> BaseModule | None:
        """Возвращает модуль по ID или None."""
        return self._modules.get(module_id)

    def all_modules(self) -> list[BaseModule]:
        """Все модули в порядке регистрации."""
        return list(self._modules.values())

    def __iter__(self) -> Iterator[BaseModule]:
        return iter(self._modules.values())

    def __len__(self) -> int:
        return len(self._modules)