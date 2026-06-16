from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QTime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QTabWidget, QTimeEdit, QVBoxLayout, QWidget,
)

from modules.schedule_tracker.logic.engine import (
    DAY_NAMES, LESSON_TYPES, Lesson, ScheduleEngine,
)
from ui.themes.scifi_dark import (
    ACCENT, ACCENT2, BG_DEEP, BG_ELEVATED, BG_SURFACE,
    BORDER, SUCCESS, TEXT, TEXT_MUTED, TEXT_BRIGHT,
)

_PIE_COLORS = ["#00D4FF", "#39FF14", "#FFD700", "#A855F7", "#FF6B35", "#64748B"]


class _Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background: {BORDER}; max-height: 1px; border: none;")


class _LessonCard(QWidget):
    def __init__(
        self,
        lesson: Lesson,
        on_click: "function",   # type: ignore[type-arg]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._lesson  = lesson
        self._on_click = on_click
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        opacity = "0.45" if not self._lesson.is_active else "1"
        color   = self._lesson.color

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color}22;
                border: 1px solid {color};
                border-left: 4px solid {color};
                border-radius: 4px;
                opacity: {opacity};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        time_lbl = QLabel(f"{self._lesson.time_start}–{self._lesson.time_end}")
        time_lbl.setStyleSheet(f"color: {color}; font-size: 10px; border: none; background: transparent;")
        layout.addWidget(time_lbl)

        title_lbl = QLabel(self._lesson.title)
        title_lbl.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 12px; font-weight: bold; border: none; background: transparent;")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        meta = []
        if self._lesson.room:
            meta.append(f"📍 {self._lesson.room}")
        if self._lesson.teacher:
            meta.append(f"👤 {self._lesson.teacher}")
        if meta:
            meta_lbl = QLabel("  ".join(meta))
            meta_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; border: none; background: transparent;")
            layout.addWidget(meta_lbl)

        if not self._lesson.is_active:
            cancelled = QLabel("ОТМЕНЕНО")
            cancelled.setStyleSheet(f"color: {ACCENT2}; font-size: 9px; letter-spacing: 2px; border: none; background: transparent;")
            layout.addWidget(cancelled)

    def mousePressEvent(self, event: object) -> None:  # type: ignore[override]
        self._on_click(self._lesson)


class _WorkloadBarChart(QWidget):
    """Столбчатая диаграмма нагрузки по дням недели."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, float] = {}
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: dict[str, float]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if not self._data:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Нет данных")
            painter.end()
            return

        pad_l, pad_r, pad_t, pad_b = 36, 12, 16, 32
        chart_w = w - pad_l - pad_r
        chart_h = h - pad_t - pad_b

        max_val = max(self._data.values()) or 1
        n  = len(self._data)
        bw = int(chart_w / n * 0.6)
        gap = int(chart_w / n)

        # Горизонтальные линии сетки
        painter.setPen(QPen(QColor(BORDER), 1))
        for i in range(5):
            y = pad_t + int(chart_h * i / 4)
            painter.drawLine(pad_l, y, w - pad_r, y)
            val = round(max_val * (4 - i) / 4, 1)
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(QFont("Consolas", 8))
            painter.drawText(0, y - 8, pad_l - 4, 16, Qt.AlignmentFlag.AlignRight, str(val))
            painter.setPen(QPen(QColor(BORDER), 1))

        # Столбцы
        for i, (day, hours) in enumerate(self._data.items()):
            bar_h = int(chart_h * hours / max_val) if max_val else 0
            x = pad_l + i * gap + (gap - bw) // 2
            y = pad_t + chart_h - bar_h

            color = QColor(ACCENT)
            if hours == max(self._data.values()):
                color = QColor(ACCENT2)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(x, y, bw, bar_h, 3, 3)

            # Подпись значения
            if hours > 0:
                painter.setPen(QColor(TEXT_BRIGHT))
                painter.setFont(QFont("Consolas", 8))
                painter.drawText(x, y - 14, bw, 14, Qt.AlignmentFlag.AlignCenter, f"{hours:.1f}")

            # Подпись дня
            short_day = day[:2]
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(QFont("Consolas", 9))
            painter.drawText(x, h - pad_b + 4, bw, pad_b - 4, Qt.AlignmentFlag.AlignCenter, short_day)

        painter.end()


class _WorkloadPieChart(QWidget):
    """Круговая диаграмма нагрузки по типам занятий."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, float] = {}
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: dict[str, float]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        if not self._data:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Нет данных")
            painter.end()
            return

        size  = min(w, h) - 40
        x     = (w - size) // 2
        y     = (h - size) // 2
        total = sum(self._data.values()) or 1
        angle = 90 * 16

        for i, (_, hours) in enumerate(self._data.items()):
            span  = int(hours / total * 360 * 16)
            color = QColor(_PIE_COLORS[i % len(_PIE_COLORS)])
            painter.setPen(QPen(QColor(BG_DEEP), 2))
            painter.setBrush(QBrush(color))
            painter.drawPie(x, y, size, size, angle, span)
            angle += span

        inner = int(size * 0.42)
        ix    = (w - inner) // 2
        iy    = (h - inner) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BG_DEEP)))
        painter.drawEllipse(ix, iy, inner, inner)

        painter.setPen(QColor(TEXT_BRIGHT))
        painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        painter.drawText(ix, iy, inner, inner, Qt.AlignmentFlag.AlignCenter,
                         f"{total:.1f}\nч/нед")
        painter.end()


class _LessonDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        lesson: Optional[Lesson] = None,
    ) -> None:
        super().__init__(parent)
        self._lesson = lesson
        self.setWindowTitle("Редактировать занятие" if lesson else "Новое занятие")
        self.setMinimumWidth(420)
        self._build_ui()
        if lesson:
            self._fill(lesson)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        def row(label: str, widget: QWidget) -> None:
            layout.addWidget(QLabel(label))
            layout.addWidget(widget)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Математический анализ")
        row("Название *", self._title_edit)

        self._teacher_edit = QLineEdit()
        self._teacher_edit.setPlaceholderText("Иванов И.И.")
        row("Преподаватель", self._teacher_edit)

        self._room_edit = QLineEdit()
        self._room_edit.setPlaceholderText("А-101")
        row("Аудитория", self._room_edit)

        self._type_combo = QComboBox()
        for key, label in LESSON_TYPES.items():
            self._type_combo.addItem(label, key)
        row("Тип занятия", self._type_combo)

        self._day_combo = QComboBox()
        for i, name in enumerate(DAY_NAMES):
            self._day_combo.addItem(name, i)
        row("День недели", self._day_combo)

        time_row = QHBoxLayout()
        self._time_start = QTimeEdit()
        self._time_start.setDisplayFormat("HH:mm")
        self._time_start.setTime(QTime(9, 0))
        self._time_end = QTimeEdit()
        self._time_end.setDisplayFormat("HH:mm")
        self._time_end.setTime(QTime(10, 30))
        time_row.addWidget(QLabel("Начало"))
        time_row.addWidget(self._time_start)
        time_row.addSpacing(12)
        time_row.addWidget(QLabel("Конец"))
        time_row.addWidget(self._time_end)
        layout.addLayout(time_row)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        self._error_lbl.setWordWrap(True)
        layout.addWidget(self._error_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _fill(self, lesson: Lesson) -> None:
        self._title_edit.setText(lesson.title)
        self._teacher_edit.setText(lesson.teacher)
        self._room_edit.setText(lesson.room)
        idx = self._type_combo.findData(lesson.lesson_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._day_combo.setCurrentIndex(lesson.day_of_week)
        h_s, m_s = map(int, lesson.time_start.split(":"))
        h_e, m_e = map(int, lesson.time_end.split(":"))
        self._time_start.setTime(QTime(h_s, m_s))
        self._time_end.setTime(QTime(h_e, m_e))

    def _on_accept(self) -> None:
        self._error_lbl.setText("")
        if not self._title_edit.text().strip():
            self._error_lbl.setText("Введите название занятия")
            return
        ts = self._time_start.time()
        te = self._time_end.time()
        if te <= ts:
            self._error_lbl.setText("Время окончания должно быть позже начала")
            return
        self.accept()

    def get_data(self) -> dict:
        ts = self._time_start.time()
        te = self._time_end.time()
        return {
            "title":       self._title_edit.text().strip(),
            "teacher":     self._teacher_edit.text().strip(),
            "room":        self._room_edit.text().strip(),
            "lesson_type": self._type_combo.currentData(),
            "day_of_week": self._day_combo.currentData(),
            "time_start":  f"{ts.hour():02d}:{ts.minute():02d}",
            "time_end":    f"{te.hour():02d}:{te.minute():02d}",
        }


class _WeekTab(QWidget):
    """Сетка недели: 7 колонок (дни), карточки занятий."""

    def __init__(self, engine: ScheduleEngine,
                 on_add: "function",    # type: ignore[type-arg]
                 on_edit: "function",   # type: ignore[type-arg]
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine  = engine
        self._on_add  = on_add
        self._on_edit = on_edit
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        lbl = QLabel("РАСПИСАНИЕ НА НЕДЕЛЮ")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        top.addWidget(lbl)
        top.addStretch()
        add_btn = QPushButton("+ Добавить занятие")
        add_btn.clicked.connect(self._on_add)
        top.addWidget(add_btn)
        layout.addLayout(top)
        layout.addWidget(_Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        grid_widget = QWidget()
        self._grid = QGridLayout(grid_widget)
        self._grid.setSpacing(6)
        self._grid.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        # Очищаем сетку
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Заголовки дней
        for col, name in enumerate(DAY_NAMES):
            hdr = QLabel(name[:2].upper())
            hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hdr.setFixedHeight(28)
            hdr.setStyleSheet(
                f"color: {ACCENT}; font-size: 11px; letter-spacing: 2px; "
                f"background: {BG_ELEVATED}; border-radius: 3px;"
            )
            self._grid.addWidget(hdr, 0, col)

        # Карточки занятий
        row_offsets = [1] * 7
        for day in range(7):
            lessons = self._engine.get_by_day(day)
            if not lessons:
                empty = QLabel("—")
                empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty.setStyleSheet(f"color: {BORDER}; font-size: 18px;")
                self._grid.addWidget(empty, 1, day)
                row_offsets[day] = 2
                continue
            for lesson in lessons:
                card = _LessonCard(lesson, on_click=self._on_edit)
                self._grid.addWidget(card, row_offsets[day], day)
                row_offsets[day] += 1

        # Выравниваем колонки
        for col in range(7):
            self._grid.setColumnStretch(col, 1)


class _TimerTab(QWidget):
    """Таймер обратного отсчёта до следующей пары. Обновляется каждую секунду."""

    def __init__(self, engine: ScheduleEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self._tick()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        header_lbl = QLabel("СЛЕДУЮЩАЯ ПАРА")
        header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 3px;")
        layout.addWidget(header_lbl)

        self._lesson_lbl = QLabel("—")
        self._lesson_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lesson_lbl.setStyleSheet(
            f"color: {TEXT_BRIGHT}; font-size: 22px; font-weight: bold;"
        )
        self._lesson_lbl.setWordWrap(True)
        layout.addWidget(self._lesson_lbl)

        self._meta_lbl = QLabel("")
        self._meta_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._meta_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(self._meta_lbl)

        layout.addWidget(_Divider())

        countdown_hdr = QLabel("ОСТАЛОСЬ")
        countdown_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        countdown_hdr.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 3px;")
        layout.addWidget(countdown_hdr)

        self._countdown_lbl = QLabel("--:--:--")
        self._countdown_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_lbl.setFont(QFont("Consolas", 56, QFont.Weight.Bold))
        self._countdown_lbl.setStyleSheet(f"color: {ACCENT};")
        layout.addWidget(self._countdown_lbl)

        # Текущее занятие
        layout.addWidget(_Divider())

        current_hdr = QLabel("СЕЙЧАС ИДЁТ")
        current_hdr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_hdr.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 3px;")
        layout.addWidget(current_hdr)

        self._current_lbl = QLabel("—")
        self._current_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._current_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self._current_lbl)

    def _tick(self) -> None:
        """Вызывается каждую секунду."""
        # Текущее занятие
        current = self._engine.current_lesson()
        if current:
            self._current_lbl.setText(
                f"{current.emoji_type}{current.title} · {current.time_start}–{current.time_end}"
                if hasattr(current, "emoji_type") else
                f"{current.title} · {current.time_start}–{current.time_end}"
            )
            self._current_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 16px; font-weight: bold;")
        else:
            self._current_lbl.setText("Нет активных занятий")
            self._current_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 14px;")

        # Следующее занятие
        result = self._engine.next_lesson()
        if result is None:
            self._lesson_lbl.setText("Занятий нет")
            self._meta_lbl.setText("")
            self._countdown_lbl.setText("--:--:--")
            return

        lesson, delta = result
        total_sec = int(delta.total_seconds())
        hours   = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        seconds = total_sec % 60

        self._lesson_lbl.setText(lesson.title)
        meta_parts = [lesson.day_name, f"{lesson.time_start}–{lesson.time_end}"]
        if lesson.room:
            meta_parts.append(f"ауд. {lesson.room}")
        if lesson.teacher:
            meta_parts.append(lesson.teacher)
        self._meta_lbl.setText("  ·  ".join(meta_parts))

        self._countdown_lbl.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        # Цвет: красный если < 15 мин
        if total_sec < 900:
            self._countdown_lbl.setStyleSheet(f"color: {ACCENT2};")
        elif total_sec < 3600:
            self._countdown_lbl.setStyleSheet(f"color: {SUCCESS};")
        else:
            self._countdown_lbl.setStyleSheet(f"color: {ACCENT};")

    def refresh(self) -> None:
        self._tick()


class _WorkloadTab(QWidget):
    """Вкладка нагрузки: столбчатая + круговая диаграммы."""

    def __init__(self, engine: ScheduleEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        lbl = QLabel("УЧЕБНАЯ НАГРУЗКА")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        header.addWidget(lbl)
        header.addStretch()
        self._total_lbl = QLabel("")
        self._total_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        header.addWidget(self._total_lbl)
        layout.addLayout(header)
        layout.addWidget(_Divider())

        charts_row = QHBoxLayout()
        charts_row.setSpacing(24)

        # Левая часть: столбчатая по дням
        left = QVBoxLayout()
        bar_title = QLabel("ЧАСОВ ПО ДНЯМ НЕДЕЛИ")
        bar_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 1px;")
        left.addWidget(bar_title)
        self._bar_chart = _WorkloadBarChart()
        left.addWidget(self._bar_chart, stretch=1)
        charts_row.addLayout(left, stretch=3)

        # Правая часть: круговая по типам + легенда
        right = QVBoxLayout()
        pie_title = QLabel("ПО ТИПАМ ЗАНЯТИЙ")
        pie_title.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 1px;")
        right.addWidget(pie_title)
        self._pie_chart = _WorkloadPieChart()
        right.addWidget(self._pie_chart, stretch=1)
        self._legend_layout = QVBoxLayout()
        right.addLayout(self._legend_layout)
        charts_row.addLayout(right, stretch=2)

        layout.addLayout(charts_row, stretch=1)

    def refresh(self) -> None:
        hours_day  = self._engine.hours_per_day()
        hours_type = self._engine.hours_per_type()
        total      = self._engine.total_hours_per_week()

        self._total_lbl.setText(f"Итого: {total:.1f} ак.ч / неделю")
        self._bar_chart.set_data(hours_day)
        self._pie_chart.set_data(hours_type)

        # Перестраиваем легенду
        while self._legend_layout.count():
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (label, hours) in enumerate(hours_type.items()):
            color = _PIE_COLORS[i % len(_PIE_COLORS)]
            row_w = QWidget()
            row   = QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            dot.setFixedWidth(18)
            row.addWidget(dot)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            row.addWidget(name_lbl, stretch=1)
            hrs_lbl = QLabel(f"{hours:.1f} ч")
            hrs_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            row.addWidget(hrs_lbl)
            self._legend_layout.addWidget(row_w)


class _AllLessonsTab(QWidget):
    """Список всех занятий с кнопками редактирования, удаления и переключения статуса."""

    def __init__(
        self,
        engine: ScheduleEngine,
        on_add:    "function",  # type: ignore[type-arg]
        on_edit:   "function",  # type: ignore[type-arg]
        on_delete: "function",  # type: ignore[type-arg]
        on_toggle: "function",  # type: ignore[type-arg]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine    = engine
        self._on_add    = on_add
        self._on_edit   = on_edit
        self._on_delete = on_delete
        self._on_toggle = on_toggle
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        lbl = QLabel("ВСЕ ЗАНЯТИЯ")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        top.addWidget(lbl)
        top.addStretch()
        add_btn = QPushButton("+ Добавить")
        add_btn.clicked.connect(self._on_add)
        top.addWidget(add_btn)
        layout.addLayout(top)
        layout.addWidget(_Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setSpacing(6)
        self._list_layout.setContentsMargins(0, 0, 4, 0)
        self._list_layout.addStretch()
        scroll.setWidget(self._container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        all_lessons = self._engine.get_all()
        if not all_lessons:
            empty = QLabel("Занятий нет.\nНажмите «+ Добавить» чтобы создать первое.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; margin: 30px;")
            self._list_layout.insertWidget(0, empty)
            return

        # Сортируем по дню и времени
        sorted_lessons = sorted(all_lessons, key=lambda l: (l.day_of_week, l.time_start))
        for lesson in sorted_lessons:
            row = self._make_row(lesson)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_row(self, lesson: Lesson) -> QWidget:
        card = QWidget()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)

        # Цветная полоска
        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        color_bar.setStyleSheet(f"background: {lesson.color}; border-radius: 2px; border: none;")
        layout.addWidget(color_bar)
        layout.addSpacing(8)

        # Информация
        info = QVBoxLayout()
        title_row = QHBoxLayout()
        title_lbl = QLabel(f"{lesson.title}")
        title_lbl.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 13px; font-weight: bold;")
        title_row.addWidget(title_lbl)
        type_lbl = QLabel(lesson.type_label)
        type_lbl.setStyleSheet(
            f"color: {lesson.color}; font-size: 10px; "
            f"background: {lesson.color}22; border-radius: 3px; padding: 2px 6px;"
        )
        title_row.addWidget(type_lbl)
        if not lesson.is_active:
            cancelled_lbl = QLabel("ОТМЕНЕНО")
            cancelled_lbl.setStyleSheet(
                f"color: {ACCENT2}; font-size: 10px; "
                f"background: {ACCENT2}22; border-radius: 3px; padding: 2px 6px;"
            )
            title_row.addWidget(cancelled_lbl)
        title_row.addStretch()
        info.addLayout(title_row)

        meta_parts = [
            lesson.day_name,
            f"{lesson.time_start}–{lesson.time_end}",
        ]
        if lesson.room:
            meta_parts.append(f"📍 {lesson.room}")
        if lesson.teacher:
            meta_parts.append(f"👤 {lesson.teacher}")
        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        info.addLayout(meta_lbl.parent().layout() if False else (info.addWidget(meta_lbl), info)[1])

        layout.addLayout(info, stretch=1)

        # Кнопки
        toggle_btn = QPushButton("●" if lesson.is_active else "○")
        toggle_btn.setFixedSize(32, 32)
        toggle_btn.setToolTip("Отменить / восстановить")
        toggle_color = SUCCESS if lesson.is_active else TEXT_MUTED
        toggle_btn.setStyleSheet(f"color: {toggle_color}; border-color: {toggle_color};")
        toggle_btn.clicked.connect(lambda _, lid=lesson.id: self._on_toggle(lid))
        layout.addWidget(toggle_btn)

        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setStyleSheet(f"color: {TEXT_MUTED}; border-color: {BORDER};")
        edit_btn.clicked.connect(lambda _, l=lesson: self._on_edit(l))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(32, 32)
        del_btn.setStyleSheet(f"color: {ACCENT2}; border-color: {ACCENT2};")
        del_btn.clicked.connect(lambda _, lid=lesson.id, name=lesson.title: self._on_delete(lid, name))
        layout.addWidget(del_btn)

        return card


class ScheduleView(QWidget):
    """Главный виджет расписания занятий с четырьмя вкладками."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._engine = ScheduleEngine()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("SCHEDULE TRACKER")
        title.setObjectName("ModuleTitle")
        header.addWidget(title)
        header.addStretch()
        subtitle = QLabel("// SQLITE STORAGE")
        subtitle.setObjectName("ModuleSubtitle")
        header.addWidget(subtitle)
        root.addLayout(header)

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

        self._week_tab     = _WeekTab(self._engine, self._on_add, self._on_edit_card)
        self._timer_tab    = _TimerTab(self._engine)
        self._workload_tab = _WorkloadTab(self._engine)
        self._list_tab     = _AllLessonsTab(
            self._engine,
            on_add=self._on_add,
            on_edit=self._on_edit_card,
            on_delete=self._on_delete,
            on_toggle=self._on_toggle,
        )

        self._tabs.addTab(self._week_tab,     "НЕДЕЛЯ")
        self._tabs.addTab(self._timer_tab,    "ТАЙМЕР")
        self._tabs.addTab(self._workload_tab, "НАГРУЗКА")
        self._tabs.addTab(self._list_tab,     "ВСЕ ЗАНЯТИЯ")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        root.addWidget(self._tabs, stretch=1)

    def _on_tab_changed(self, index: int) -> None:
        match index:
            case 0: self._week_tab.refresh()
            case 1: self._timer_tab.refresh()
            case 2: self._workload_tab.refresh()
            case 3: self._list_tab.refresh()

    def _on_data_changed(self) -> None:
        self._week_tab.refresh()
        self._list_tab.refresh()
        self._workload_tab.refresh()
        self._timer_tab.refresh()

    def _on_add(self) -> None:
        dlg = _LessonDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self._engine.add_lesson(**data)
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_edit_card(self, lesson: Lesson) -> None:
        dlg = _LessonDialog(self, lesson=lesson)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self._engine.edit_lesson(lesson_id=lesson.id, **data)
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_delete(self, lesson_id: str, name: str) -> None:
        reply = QMessageBox.question(
            self, "Удалить занятие",
            f"Удалить «{name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._engine.delete_lesson(lesson_id)
            self._on_data_changed()

    def _on_toggle(self, lesson_id: str) -> None:
        self._engine.toggle_active(lesson_id)
        self._on_data_changed()

    def refresh(self) -> None:
        """Вызывается хуком on_activated."""
        self._week_tab.refresh()