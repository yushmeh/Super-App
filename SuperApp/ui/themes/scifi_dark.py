from __future__ import annotations

BG_DEEP       = "#0A0E17"
BG_SURFACE    = "#111827"
BG_ELEVATED   = "#1A2332"
BORDER        = "#1E2D3D"
BORDER_ACCENT = "#00D4FF33"

ACCENT        = "#00D4FF"
ACCENT_DARK   = "#0088AA"
ACCENT2       = "#FF6B35"
SUCCESS       = "#39FF14"

TEXT          = "#E2E8F0"
TEXT_MUTED    = "#64748B"
TEXT_BRIGHT   = "#F8FAFC"

PLOT_BG       = "#0D1421"
PLOT_GRID     = "#1E2D3D"
PLOT_LINE     = "#00D4FF"
PLOT_LINE_ALT = "#FF6B35"
PLOT_FILL     = "#00D4FF18"


GLOBAL_QSS = f"""
QMainWindow, QWidget {{
    background-color: {BG_DEEP};
    color: {TEXT};
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}}

#NavSidebar {{
    background-color: {BG_SURFACE};
    border-right: 1px solid {BORDER};
    min-width: 220px;
    max-width: 220px;
}}

#NavTitle {{
    color: {ACCENT};
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 20px 16px 8px 16px;
    font-family: "Consolas", monospace;
}}

#NavSubtitle {{
    color: {TEXT_MUTED};
    font-size: 10px;
    letter-spacing: 2px;
    padding: 0px 16px 20px 16px;
}}

#NavDivider {{
    background-color: {BORDER};
    max-height: 1px;
    margin: 4px 16px;
}}

#NavButton {{
    background-color: transparent;
    color: {TEXT_MUTED};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    font-family: "Consolas", monospace;
    letter-spacing: 1px;
}}

#NavButton:hover {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
    border-left: 3px solid {ACCENT_DARK};
}}

#NavButton[active="true"] {{
    background-color: {BG_ELEVATED};
    color: {ACCENT};
    border-left: 3px solid {ACCENT};
    font-weight: bold;
}}

#ContentArea {{
    background-color: {BG_DEEP};
}}

#ModuleTitle {{
    color: {TEXT_BRIGHT};
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 2px;
    font-family: "Consolas", monospace;
}}

#ModuleSubtitle {{
    color: {TEXT_MUTED};
    font-size: 11px;
    letter-spacing: 1px;
}}

#Card {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 16px;
}}

QComboBox {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 12px;
    color: {TEXT};
    font-family: "Consolas", monospace;
    min-width: 140px;
}}

QComboBox:hover {{
    border-color: {ACCENT_DARK};
}}

QComboBox:focus {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {ACCENT};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_ELEVATED};
    border: 1px solid {ACCENT};
    color: {TEXT};
    selection-background-color: {ACCENT_DARK};
    outline: none;
}}

QPushButton {{
    background-color: {BG_ELEVATED};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    color: {ACCENT};
    padding: 7px 18px;
    font-family: "Consolas", monospace;
    font-size: 12px;
    letter-spacing: 1px;
}}

QPushButton:hover {{
    background-color: {ACCENT};
    color: {BG_DEEP};
}}

QPushButton:pressed {{
    background-color: {ACCENT_DARK};
    color: {TEXT};
}}

QPushButton:disabled {{
    border-color: {BORDER};
    color: {TEXT_MUTED};
    background-color: {BG_SURFACE};
}}

QRadioButton {{
    color: {TEXT};
    spacing: 8px;
    font-family: "Consolas", monospace;
}}

QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 2px solid {BORDER};
    background-color: {BG_ELEVATED};
}}

QRadioButton::indicator:checked {{
    border-color: {ACCENT};
    background-color: {ACCENT};
}}

QRadioButton::indicator:hover {{
    border-color: {ACCENT_DARK};
}}

QDateEdit {{
    background-color: {BG_ELEVATED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    color: {TEXT};
    font-family: "Consolas", monospace;
}}

QDateEdit:focus {{
    border-color: {ACCENT};
}}

QDateEdit::up-button, QDateEdit::down-button {{
    background-color: {BG_ELEVATED};
    border: none;
    width: 16px;
}}

QCalendarWidget {{
    background-color: {BG_SURFACE};
    color: {TEXT};
}}

QCalendarWidget QWidget {{
    background-color: {BG_SURFACE};
    color: {TEXT};
}}

QCalendarWidget QAbstractItemView {{
    background-color: {BG_SURFACE};
    selection-background-color: {ACCENT};
    selection-color: {BG_DEEP};
    color: {TEXT};
}}

QLabel {{
    color: {TEXT};
    font-family: "Consolas", monospace;
}}

QScrollBar:vertical {{
    background: {BG_SURFACE};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_DARK};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolTip {{
    background-color: {BG_ELEVATED};
    border: 1px solid {ACCENT};
    color: {TEXT};
    padding: 4px 8px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}}
"""