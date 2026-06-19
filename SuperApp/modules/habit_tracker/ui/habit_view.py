from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTabWidget, QVBoxLayout, QWidget, QFrame,
)

from modules.habit_tracker.logic.service import (
    Habit, HabitService, DONE, SKIPPED, NONE,
)
from ui.themes.scifi_dark import (
    ACCENT, ACCENT2, BG_DEEP, BG_ELEVATED, BG_SURFACE,
    BORDER, SUCCESS, TEXT, TEXT_MUTED, TEXT_BRIGHT,
)

# Цвета тепловой карты
_HEAT_NONE    = "#1A2332"
_HEAT_DONE    = "#00D4FF"
_HEAT_SKIP    = "#FF6B35"
_HEAT_DONE_DIM = "#004D5A"

_EMOJI_OPTIONS = [
    "⭐", "💪", "🏃", "📚", "💧", "🧘", "🎯", "🛌", "🥗", "✍️",
    "🎵", "🧹", "💊", "🚴", "🌿", "🧠", "🎨", "📝", "🏋️", "😴",
]

class _Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background-color: {BORDER}; max-height: 1px; border: none;")


class _HeatmapWidget(QWidget):
    """
    Тепловая карта в стиле GitHub: 18 недель × 7 дней.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._habit: Optional[Habit] = None
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_habit(self, habit: Optional[Habit]) -> None:
        self._habit = habit
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._habit is None:
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(QFont("Consolas", 11))
            painter.drawText(
                self.rect(), Qt.AlignmentFlag.AlignCenter,
                "Выберите привычку для просмотра карты"
            )
            painter.end()
            return

        cell  = 14
        gap   = 3
        step  = cell + gap
        pad_l = 32   # отступ слева для подписей дней недели
        pad_t = 24   # отступ сверху для подписей месяцев

        data = self._habit.get_heatmap_data(18)

        # Группируем по неделям
        weeks: list[list[tuple[date, str]]] = []
        week: list[tuple[date, str]] = []
        for item in data:
            week.append(item)
            if len(week) == 7:
                weeks.append(week)
                week = []
        if week:
            weeks.append(week)

        # Подписи дней недели
        day_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        painter.setFont(QFont("Consolas", 8))
        painter.setPen(QColor(TEXT_MUTED))
        for i, name in enumerate(day_names):
            y = pad_t + i * step + cell // 2 + 4
            painter.drawText(0, y - 8, pad_l - 4, cell, Qt.AlignmentFlag.AlignRight, name)

        # Подписи месяцев над колонками
        last_month = -1
        for col, wk in enumerate(weeks):
            if wk and wk[0][0].month != last_month:
                last_month = wk[0][0].month
                month_name = wk[0][0].strftime("%b")
                x = pad_l + col * step
                painter.drawText(x, 0, step * 3, pad_t, Qt.AlignmentFlag.AlignLeft, month_name)

        # Ячейки
        for col, wk in enumerate(weeks):
            for row, (day, status) in enumerate(wk):
                x = pad_l + col * step
                y = pad_t + row * step

                if status == DONE:
                    color = QColor(_HEAT_DONE)
                elif status == SKIPPED:
                    color = QColor(_HEAT_SKIP)
                else:
                    color = QColor(_HEAT_NONE)

                # Сегодня — обводка
                if day == date.today():
                    painter.setPen(QPen(QColor(ACCENT), 1.5))
                else:
                    painter.setPen(Qt.PenStyle.NoPen)

                painter.setBrush(QBrush(color))
                painter.drawRoundedRect(x, y, cell, cell, 2, 2)

        painter.end()


class _MiniStreakBar(QWidget):
    """Горизонтальная мини-полоска последних 30 дней для карточки привычки."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._habit: Optional[Habit] = None
        self.setFixedHeight(10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_habit(self, habit: Habit) -> None:
        self._habit = habit
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        if self._habit is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        days  = 30
        today = date.today()
        w     = self.width()
        h     = self.height()
        cell  = max(4, (w - days) // days)
        gap   = 1

        for i in range(days):
            day    = today - timedelta(days=days - 1 - i)
            status = self._habit.log.get(day.isoformat(), NONE)
            x      = i * (cell + gap)

            if status == DONE:
                color = QColor(_HEAT_DONE)
            elif status == SKIPPED:
                color = QColor(_HEAT_SKIP)
            else:
                color = QColor(_HEAT_NONE)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, 0, cell, h, 2, 2)

        painter.end()

class _AddHabitDialog(QDialog):
    def __init__(self, parent: QWidget | None = None,
                 name: str = "", emoji: str = "⭐") -> None:
        super().__init__(parent)
        self.setWindowTitle("Новая привычка" if not name else "Редактировать привычку")
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Например: Пить 2 литра воды")
        self.name_edit.setMaxLength(60)
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Иконка:"))
        self.emoji_combo = QComboBox()
        for e in _EMOJI_OPTIONS:
            self.emoji_combo.addItem(e, e)
        idx = self.emoji_combo.findData(emoji)
        if idx >= 0:
            self.emoji_combo.setCurrentIndex(idx)
        layout.addWidget(self.emoji_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._error = QLabel("")
        self._error.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        layout.addWidget(self._error)

    def accept(self) -> None:
        if not self.name_edit.text().strip():
            self._error.setText("Введите название привычки")
            return
        super().accept()

    def get_data(self) -> tuple[str, str]:
        return self.name_edit.text().strip(), self.emoji_combo.currentData()

class _HabitCard(QWidget):
    """
    Карточка одной привычки в списке «Сегодня».
    """

    def __init__(
        self,
        habit: Habit,
        on_mark:   "function",  # type: ignore[type-arg]
        on_rename: "function",  # type: ignore[type-arg]
        on_delete: "function",  # type: ignore[type-arg]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._habit    = habit
        self._on_mark   = on_mark
        self._on_rename = on_rename
        self._on_delete = on_delete
        self.setObjectName("Card")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Верхняя строка: иконка + имя + кнопки
        top = QHBoxLayout()

        self._title_label = QLabel(f"{self._habit.emoji}  {self._habit.name}")
        self._title_label.setStyleSheet(
            f"color: {TEXT_BRIGHT}; font-size: 14px; font-weight: bold;"
        )
        top.addWidget(self._title_label, stretch=1)

        # Серии
        streak_lbl = QLabel(
            f"🔥 {self._habit.current_streak()}  "
            f"<span style='color:{TEXT_MUTED}; font-size:10px;'>лучшая: {self._habit.best_streak()}</span>"
        )
        streak_lbl.setTextFormat(Qt.TextFormat.RichText)
        streak_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 12px;")
        top.addWidget(streak_lbl)

        layout.addLayout(top)

        # Мини-полоска 30 дней
        bar = _MiniStreakBar()
        bar.set_habit(self._habit)
        layout.addWidget(bar)

        # Нижняя строка: статус сегодня + кнопки действий
        bottom = QHBoxLayout()

        today_status = self._habit.status_on(date.today())
        rate = self._habit.completion_rate(30)
        rate_lbl = QLabel(f"{rate:.0f}% за 30 дней")
        rate_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        bottom.addWidget(rate_lbl)
        bottom.addStretch()

        # Кнопка "Выполнено"
        done_btn = QPushButton("✓")
        done_btn.setFixedSize(32, 32)
        done_btn.setToolTip("Выполнено")
        if today_status == DONE:
            done_btn.setStyleSheet(
                f"background-color: {SUCCESS}; color: {BG_DEEP}; "
                f"border: none; border-radius: 4px; font-weight: bold;"
            )
        done_btn.clicked.connect(lambda: self._on_mark(self._habit.id, DONE))
        bottom.addWidget(done_btn)

        # Кнопка "Пропущено"
        skip_btn = QPushButton("✗")
        skip_btn.setFixedSize(32, 32)
        skip_btn.setToolTip("Пропустить")
        if today_status == SKIPPED:
            skip_btn.setStyleSheet(
                f"background-color: {ACCENT2}; color: {BG_DEEP}; "
                f"border: none; border-radius: 4px; font-weight: bold;"
            )
        skip_btn.clicked.connect(lambda: self._on_mark(self._habit.id, SKIPPED))
        bottom.addWidget(skip_btn)

        # Кнопка редактирования
        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setToolTip("Переименовать")
        edit_btn.setStyleSheet(f"border-color: {TEXT_MUTED}; color: {TEXT_MUTED};")
        edit_btn.clicked.connect(lambda: self._on_rename(self._habit.id, self._habit.name, self._habit.emoji))
        bottom.addWidget(edit_btn)

        # Кнопка удаления
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(32, 32)
        del_btn.setToolTip("Удалить")
        del_btn.setStyleSheet(f"border-color: {ACCENT2}; color: {ACCENT2};")
        del_btn.clicked.connect(lambda: self._on_delete(self._habit.id, self._habit.name))
        bottom.addWidget(del_btn)

        layout.addLayout(bottom)

class _TodayTab(QWidget):
    """Вкладка «Сегодня»: список всех привычек с карточками."""

    def __init__(self, service: HabitService,
                 on_data_changed: "function",  # type: ignore[type-arg]
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._on_data_changed = on_data_changed
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        # Верхняя панель
        top = QHBoxLayout()
        today_str = date.today().strftime("%A, %d %B %Y")
        date_lbl = QLabel(today_str.upper())
        date_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        top.addWidget(date_lbl)
        top.addStretch()

        add_btn = QPushButton("+ Добавить привычку")
        add_btn.clicked.connect(self._on_add)
        top.addWidget(add_btn)
        layout.addLayout(top)

        layout.addWidget(_Divider())

        # Прокручиваемый список карточек
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setSpacing(8)
        self._cards_layout.setContentsMargins(0, 0, 4, 0)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll, stretch=1)

        # Сводка дня внизу
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 1px;"
        )
        self._summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._summary_label)

    def refresh(self) -> None:
        # Очищаем карточки
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        habits = self._service.get_habits()

        if not habits:
            empty = QLabel(
                "Привычек пока нет.\n"
                "Нажмите «+ Добавить привычку» чтобы начать."
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; margin: 40px;")
            self._cards_layout.insertWidget(0, empty)
            self._summary_label.setText("")
            return

        for habit in habits:
            card = _HabitCard(
                habit=habit,
                on_mark=self._on_mark,
                on_rename=self._on_rename,
                on_delete=self._on_delete,
            )
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        # Сводка дня
        today = date.today().isoformat()
        done_today  = sum(1 for h in habits if h.log.get(today) == DONE)
        total       = len(habits)
        self._summary_label.setText(
            f"СЕГОДНЯ: {done_today}/{total} выполнено"
        )

    def _on_add(self) -> None:
        dlg = _AddHabitDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, emoji = dlg.get_data()
            try:
                self._service.add_habit(name, emoji)
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_mark(self, habit_id: str, status: str) -> None:
        self._service.mark(habit_id, status)
        self._on_data_changed()

    def _on_rename(self, habit_id: str, current_name: str, current_emoji: str) -> None:
        dlg = _AddHabitDialog(self, name=current_name, emoji=current_emoji)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, emoji = dlg.get_data()
            try:
                self._service.rename_habit(habit_id, name)
                # Обновляем emoji напрямую
                for h in self._service._data["habits"]:  # type: ignore[attr-defined]
                    if h["id"] == habit_id:
                        h["emoji"] = emoji
                        from modules.habit_tracker.api.storage import save
                        save(self._service._data)  # type: ignore[attr-defined]
                        break
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_delete(self, habit_id: str, name: str) -> None:
        reply = QMessageBox.question(
            self,
            "Удалить привычку",
            f"Удалить «{name}»?\nВся история будет потеряна.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._service.delete_habit(habit_id)
            self._on_data_changed()


class _HeatmapTab(QWidget):
    """Вкладка «Тепловая карта» с выбором привычки."""

    def __init__(self, service: HabitService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        # Выбор привычки
        top = QHBoxLayout()
        lbl = QLabel("ПРИВЫЧКА:")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        top.addWidget(lbl)
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_habit_changed)
        top.addWidget(self._combo, stretch=1)
        layout.addLayout(top)

        layout.addWidget(_Divider())

        # Тепловая карта
        self._heatmap = _HeatmapWidget()
        layout.addWidget(self._heatmap)

        # Легенда
        legend = QHBoxLayout()
        legend.addStretch()
        for color, label in [(_HEAT_NONE, "Нет отметки"), (_HEAT_DONE, "Выполнено"), (_HEAT_SKIP, "Пропущено")]:
            dot = QLabel("■")
            dot.setStyleSheet(f"color: {color}; font-size: 16px;")
            legend.addWidget(dot)
            txt = QLabel(label)
            txt.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
            legend.addWidget(txt)
            legend.addSpacing(16)
        layout.addLayout(legend)

        # Статистика под картой
        self._stats_label = QLabel("")
        self._stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._stats_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(self._stats_label)

        layout.addStretch()

    def refresh(self) -> None:
        habits = self._service.get_habits()
        current_id = self._combo.currentData()

        self._combo.blockSignals(True)
        self._combo.clear()
        for h in habits:
            self._combo.addItem(f"{h.emoji}  {h.name}", h.id)
        self._combo.blockSignals(False)

        # Восстанавливаем выбор
        if current_id:
            idx = self._combo.findData(current_id)
            if idx >= 0:
                self._combo.setCurrentIndex(idx)

        self._update_heatmap()

    def _on_habit_changed(self) -> None:
        self._update_heatmap()

    def _update_heatmap(self) -> None:
        habit_id = self._combo.currentData()
        if not habit_id:
            self._heatmap.set_habit(None)
            self._stats_label.setText("")
            return

        habits = {h.id: h for h in self._service.get_habits()}
        habit  = habits.get(habit_id)
        self._heatmap.set_habit(habit)

        if habit:
            self._stats_label.setText(
                f"🔥 Текущая серия: {habit.current_streak()} дн.    "
                f"🏆 Лучшая серия: {habit.best_streak()} дн.    "
                f"📊 Выполнение за 30 дней: {habit.completion_rate(30):.1f}%"
            )


class _StatsTab(QWidget):
    """Вкладка «Статистика»: сводная таблица по всем привычкам."""

    def __init__(self, service: HabitService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(8)

        header_lbl = QLabel("СТАТИСТИКА ПО ПРИВЫЧКАМ")
        header_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(header_lbl)
        layout.addWidget(_Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._table_container = QWidget()
        self._table_layout = QVBoxLayout(self._table_container)
        self._table_layout.setSpacing(6)
        self._table_layout.setContentsMargins(0, 0, 4, 0)
        self._table_layout.addStretch()

        scroll.setWidget(self._table_container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        while self._table_layout.count() > 1:
            item = self._table_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        habits = self._service.get_habits()
        if not habits:
            empty = QLabel("Нет привычек для отображения статистики.")
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; margin: 20px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table_layout.insertWidget(0, empty)
            return

        # Заголовок таблицы
        self._table_layout.insertWidget(0, self._make_row(
            "ПРИВЫЧКА", "СЕРИЯ", "ЛУЧШАЯ", "30 ДНЕЙ", "ВСЕГО",
            is_header=True,
        ))

        for habit in sorted(habits, key=lambda h: h.current_streak(), reverse=True):
            total_done = sum(1 for s in habit.log.values() if s == DONE)
            row = self._make_row(
                f"{habit.emoji} {habit.name}",
                f"🔥 {habit.current_streak()}",
                f"🏆 {habit.best_streak()}",
                f"{habit.completion_rate(30):.1f}%",
                str(total_done),
            )
            self._table_layout.insertWidget(
                self._table_layout.count() - 1, row
            )

    @staticmethod
    def _make_row(*cols: str, is_header: bool = False) -> QWidget:
        w = QWidget()
        w.setObjectName("Card" if not is_header else "")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(12, 8, 12, 8)
        widths = [0, 80, 80, 80, 60]
        for i, (text, width) in enumerate(zip(cols, widths)):
            lbl = QLabel(text)
            color = TEXT_MUTED if is_header else (TEXT_BRIGHT if i == 0 else TEXT)
            size  = "10px" if is_header else "12px"
            lbl.setStyleSheet(f"color: {color}; font-size: {size};")
            if width:
                lbl.setFixedWidth(width)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            else:
                layout.addWidget(lbl, stretch=1)
                continue
            layout.addWidget(lbl)
        if is_header:
            w.setStyleSheet(f"background: {BG_ELEVATED}; border-radius: 4px;")
        return w

class HabitView(QWidget):
    """Главный виджет трекера привычек с тремя вкладками."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = HabitService()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel("HABIT TRACKER")
        title.setObjectName("ModuleTitle")
        header.addWidget(title)
        header.addStretch()

        # Кнопки экспорта/импорта
        exp_btn = QPushButton("↑ Экспорт")
        exp_btn.setFixedWidth(110)
        exp_btn.clicked.connect(self._on_export)
        header.addWidget(exp_btn)

        imp_btn = QPushButton("↓ Импорт")
        imp_btn.setFixedWidth(110)
        imp_btn.clicked.connect(self._on_import)
        header.addWidget(imp_btn)

        subtitle = QLabel("// LOCAL STORAGE")
        subtitle.setObjectName("ModuleSubtitle")
        header.addWidget(subtitle)
        root.addLayout(header)

        # Вкладки
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 6px;
                background: {BG_DEEP};
                padding: 16px;
            }}
            QTabBar::tab {{
                background: {BG_SURFACE};
                color: {TEXT_MUTED};
                padding: 8px 20px;
                border: 1px solid {BORDER};
                border-bottom: none;
                font-family: Consolas;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QTabBar::tab:selected {{
                background: {BG_ELEVATED};
                color: {ACCENT};
                border-top: 2px solid {ACCENT};
            }}
            QTabBar::tab:hover {{ color: {TEXT}; }}
        """)

        self._today_tab   = _TodayTab(self._service, self._on_data_changed)
        self._heatmap_tab = _HeatmapTab(self._service)
        self._stats_tab   = _StatsTab(self._service)

        self._tabs.addTab(self._today_tab,   "СЕГОДНЯ")
        self._tabs.addTab(self._heatmap_tab, "ТЕПЛОВАЯ КАРТА")
        self._tabs.addTab(self._stats_tab,   "СТАТИСТИКА")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        root.addWidget(self._tabs, stretch=1)

    def _on_tab_changed(self, index: int) -> None:
        match index:
            case 0: self._today_tab.refresh()
            case 1: self._heatmap_tab.refresh()
            case 2: self._stats_tab.refresh()

    def _on_data_changed(self) -> None:
        self._today_tab.refresh()
        # Обновляем другие вкладки в фоне
        self._heatmap_tab.refresh()
        self._stats_tab.refresh()

    def _on_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт привычек", "habits_export.json",
            "JSON файлы (*.json)"
        )
        if path:
            try:
                self._service.export(path)
                QMessageBox.information(self, "Экспорт", f"Данные сохранены в:\n{path}")
            except OSError as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт привычек", "",
            "JSON файлы (*.json)"
        )
        if not path:
            return

        reply = QMessageBox.question(
            self,
            "Режим импорта",
            "Объединить с текущими привычками?\n\n"
            "«Да» — добавить новые (дубли пропустятся)\n"
            "«Нет» — заменить все текущие данные",
            QMessageBox.StandardButton.Yes |
            QMessageBox.StandardButton.No |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return

        merge = reply == QMessageBox.StandardButton.Yes
        try:
            count = self._service.import_data(path, merge=merge)
            QMessageBox.information(
                self, "Импорт завершён",
                f"Импортировано привычек: {count}"
            )
            self._on_data_changed()
        except (ValueError, OSError, KeyError) as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def refresh(self) -> None:
        """Вызывается хуком on_activated."""
        self._today_tab.refresh()