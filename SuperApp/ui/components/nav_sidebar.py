"""
ui/components/nav_sidebar.py
============================
Боковая навигационная панель SuperApp.

Динамически строится из списка зарегистрированных модулей.
Испускает сигнал module_selected(module_id) при клике на кнопку.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.base_module import BaseModule


class NavSidebar(QWidget):
    """
    Боковое меню навигации.

    Сигналы:
        module_selected(str) — испускается при выборе модуля, передаёт module_id
    """

    module_selected = pyqtSignal(str)

    def __init__(self, modules: list[BaseModule], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NavSidebar")

        self._buttons: dict[str, QPushButton] = {}
        self._active_id: str | None = None

        self._build_ui(modules)

    def _build_ui(self, modules: list[BaseModule]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Логотип / заголовок ───────────────────────────────────────────
        title = QLabel("SUPER\nAPP")
        title.setObjectName("NavTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        subtitle = QLabel("// CONTROL PANEL v1.0")
        subtitle.setObjectName("NavSubtitle")
        layout.addWidget(subtitle)

        # Разделитель
        layout.addWidget(self._make_divider())

        nav_label = QLabel("  MODULES")
        nav_label.setObjectName("NavSubtitle")
        nav_label.setContentsMargins(16, 8, 0, 8)
        layout.addWidget(nav_label)

        # ── Кнопки модулей ───────────────────────────────────────────────
        for module in modules:
            btn = QPushButton(f"  ›  {module.display_name}")
            btn.setObjectName("NavButton")
            btn.setCheckable(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Замыкание через default-аргумент
            btn.clicked.connect(lambda _, mid=module.module_id: self._on_button_clicked(mid))
            self._buttons[module.module_id] = btn
            layout.addWidget(btn)

        # Распорка внизу
        layout.addStretch()

        # ── Нижняя информационная строка ─────────────────────────────────
        layout.addWidget(self._make_divider())
        status_label = QLabel("  SYS: ONLINE  ●")
        status_label.setObjectName("NavSubtitle")
        status_label.setContentsMargins(16, 8, 0, 12)
        # Зелёный цвет через inline style (не трогает тему)
        status_label.setStyleSheet("color: #39FF14; font-size: 10px;")
        layout.addWidget(status_label)

    def _make_divider(self) -> QFrame:
        divider = QFrame()
        divider.setObjectName("NavDivider")
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        return divider

    def _on_button_clicked(self, module_id: str) -> None:
        self.set_active(module_id)
        self.module_selected.emit(module_id)

    def set_active(self, module_id: str) -> None:
        """Обновляет визуальное состояние активной кнопки."""
        # Сброс предыдущей активной кнопки
        if self._active_id is not None and self._active_id in self._buttons:
            prev_btn = self._buttons[self._active_id]
            prev_btn.setProperty("active", False)
            prev_btn.style().unpolish(prev_btn)
            prev_btn.style().polish(prev_btn)

        # Активация новой кнопки
        if module_id in self._buttons:
            btn = self._buttons[module_id]
            btn.setProperty("active", True)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._active_id = module_id