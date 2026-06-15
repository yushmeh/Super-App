"""
ui/components/placeholder_screen.py
====================================
Экран-заглушка для модулей, которые ещё не реализованы.
Отображает стилизованное сообщение «ACCESS DENIED» в стиле Sci-Fi Dark
с анимацией мигающего курсора.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ui.themes.scifi_dark import ACCENT, ACCENT2, BORDER, TEXT_MUTED

_CODENAMES = [
    "util№5",
    "util№4"
]


class PlaceholderScreen(QWidget):
    """
    Виджет-заглушка с уникальным кодовым именем для каждого слота.

    Параметры:
        slot_index: порядковый номер слота (0-based)
    """

    def __init__(self, slot_index: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._slot_index = slot_index
        self._codename = _CODENAMES[slot_index % len(_CODENAMES)]
        self._blink_state = True
        self._build_ui()
        self._start_blink_timer()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        top_deco = QLabel(
            f"// MODULE SLOT [{self._slot_index + 2:02d}] //\n"
            f"// IDENTIFIER: {self._codename}"
        )
        top_deco.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_deco.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 2px;")
        layout.addWidget(top_deco)

        sep = QLabel("─" * 42)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet(f"color: {BORDER}; font-size: 13px;")
        layout.addWidget(sep)

        main_title = QLabel("ACCESS\nDENIED")
        main_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_title.setFont(QFont("Consolas", 42, QFont.Weight.Bold))
        main_title.setStyleSheet(f"color: {ACCENT2}; letter-spacing: 8px;")
        layout.addWidget(main_title)

        status = QLabel("[ CLEARANCE LEVEL INSUFFICIENT ]")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setStyleSheet(f"color: {ACCENT}; font-size: 12px; letter-spacing: 3px;")
        layout.addWidget(status)

        self._loading_label = QLabel("▌")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(f"color: {ACCENT}; font-size: 20px; margin-top: 16px;")
        layout.addWidget(self._loading_label)

        hint = QLabel("MODULE UNDER DEVELOPMENT\nETA: CLASSIFIED  //  PRIORITY: ALPHA")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 1px; margin-top: 8px;")
        layout.addWidget(hint)

    def _start_blink_timer(self) -> None:
        timer = QTimer(self)
        timer.timeout.connect(self._blink)
        timer.start(600)

    def _blink(self) -> None:
        self._blink_state = not self._blink_state
        self._loading_label.setText("▌" if self._blink_state else " ")