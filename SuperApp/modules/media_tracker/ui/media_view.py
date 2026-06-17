from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from modules.media_tracker.logic.service import (
    MEDIA_TYPES, STATUSES, MediaItem, MediaService,
)
from ui.themes.scifi_dark import (
    ACCENT, ACCENT2, BG_DEEP, BG_ELEVATED, BG_SURFACE,
    BORDER, SUCCESS, TEXT, TEXT_MUTED, TEXT_BRIGHT,
)

_PIE_COLORS = ["#00D4FF", "#A855F7", "#FFD700", "#39FF14", "#FF6B35", "#64748B"]


class _Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background: {BORDER}; max-height: 1px; border: none;")


class _StarRating(QWidget):
    """Отображение оценки 1-10 в виде заполненных/пустых звёзд (5 штук, шаг 0.5)."""

    def __init__(self, rating: Optional[int] = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rating = rating
        self.setFixedHeight(18)
        self.setMinimumWidth(130)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_rating(self, rating: Optional[int]) -> None:
        self._rating = rating
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Segoe UI Symbol", 12))

        if self._rating is None:
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignVCenter, "не оценено")
            painter.end()
            return

        filled = self._rating / 2  # из 10 в 5 звёзд
        full_stars = int(filled)
        half = filled - full_stars >= 0.5

        x = 0
        for i in range(5):
            if i < full_stars:
                painter.setPen(QColor("#FFD700"))
                painter.drawText(x, 0, 18, 18, Qt.AlignmentFlag.AlignCenter, "★")
            elif i == full_stars and half:
                painter.setPen(QColor("#FFD700"))
                painter.drawText(x, 0, 18, 18, Qt.AlignmentFlag.AlignCenter, "★")
            else:
                painter.setPen(QColor(BORDER))
                painter.drawText(x, 0, 18, 18, Qt.AlignmentFlag.AlignCenter, "☆")
            x += 16

        painter.setPen(QColor(TEXT_MUTED))
        painter.setFont(QFont("Consolas", 9))
        painter.drawText(x + 6, 0, 42, 18, Qt.AlignmentFlag.AlignVCenter, f"{self._rating}/10")
        painter.end()


class _DonutChart(QWidget):
    """Универсальная donut-диаграмма для распределений (тип/статус)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, int] = {}
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: dict[str, int]) -> None:
        self._data = {k: v for k, v in data.items() if v > 0}
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

        size  = min(w, h) - 30
        x, y  = (w - size) // 2, (h - size) // 2
        total = sum(self._data.values())
        angle = 90 * 16

        for i, (_, count) in enumerate(self._data.items()):
            span  = int(count / total * 360 * 16)
            color = QColor(_PIE_COLORS[i % len(_PIE_COLORS)])
            painter.setPen(QPen(QColor(BG_DEEP), 2))
            painter.setBrush(QBrush(color))
            painter.drawPie(x, y, size, size, angle, span)
            angle += span

        inner = int(size * 0.45)
        ix, iy = (w - inner) // 2, (h - inner) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BG_DEEP)))
        painter.drawEllipse(ix, iy, inner, inner)

        painter.setPen(QColor(TEXT_BRIGHT))
        painter.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        painter.drawText(ix, iy, inner, inner, Qt.AlignmentFlag.AlignCenter, str(total))
        painter.end()


class _ItemDialog(QDialog):
    """Диалог добавления/редактирования записи."""

    def __init__(self, parent: QWidget | None = None, item: Optional[MediaItem] = None) -> None:
        super().__init__(parent)
        self._item = item
        self.setWindowTitle("Редактировать" if item else "Добавить в каталог")
        self.setMinimumWidth(380)
        self._build_ui()
        if item:
            self._fill(item)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Название *"))
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Интерстеллар")
        layout.addWidget(self._title_edit)

        layout.addWidget(QLabel("Тип"))
        self._type_combo = QComboBox()
        for key, label in MEDIA_TYPES.items():
            self._type_combo.addItem(label, key)
        layout.addWidget(self._type_combo)

        layout.addWidget(QLabel("Статус"))
        self._status_combo = QComboBox()
        for key, label in STATUSES.items():
            self._status_combo.addItem(label, key)
        layout.addWidget(self._status_combo)

        rating_row = QHBoxLayout()
        rating_row.addWidget(QLabel("Оценка"))
        self._rating_slider = QSlider(Qt.Orientation.Horizontal)
        self._rating_slider.setRange(0, 10)  # 0 = не оценено
        self._rating_slider.setValue(0)
        self._rating_slider.valueChanged.connect(self._on_rating_changed)
        rating_row.addWidget(self._rating_slider, stretch=1)
        self._rating_value_lbl = QLabel("—")
        self._rating_value_lbl.setFixedWidth(50)
        self._rating_value_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        rating_row.addWidget(self._rating_value_lbl)
        layout.addLayout(rating_row)

        layout.addWidget(QLabel("Заметки"))
        self._notes_edit = QTextEdit()
        self._notes_edit.setFixedHeight(70)
        self._notes_edit.setPlaceholderText("Впечатления, мысли...")
        layout.addWidget(self._notes_edit)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        layout.addWidget(self._error_lbl)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_rating_changed(self, value: int) -> None:
        self._rating_value_lbl.setText("—" if value == 0 else f"{value}/10")

    def _fill(self, item: MediaItem) -> None:
        self._title_edit.setText(item.title)
        idx = self._type_combo.findData(item.media_type)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        idx = self._status_combo.findData(item.status)
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)
        self._rating_slider.setValue(item.rating or 0)
        self._notes_edit.setPlainText(item.notes)

    def _on_accept(self) -> None:
        if not self._title_edit.text().strip():
            self._error_lbl.setText("Введите название")
            return
        self.accept()

    def get_data(self) -> dict:
        rating = self._rating_slider.value()
        return {
            "title":      self._title_edit.text().strip(),
            "media_type": self._type_combo.currentData(),
            "status":     self._status_combo.currentData(),
            "rating":     rating if rating > 0 else None,
            "notes":      self._notes_edit.toPlainText().strip(),
        }


class _LibraryTab(QWidget):
    """Вкладка библиотеки с фильтрами и карточками."""

    def __init__(
        self,
        service: MediaService,
        on_add: "function",     # type: ignore[type-arg]
        on_edit: "function",    # type: ignore[type-arg]
        on_delete: "function",  # type: ignore[type-arg]
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service   = service
        self._on_add    = on_add
        self._on_edit   = on_edit
        self._on_delete = on_delete
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self._type_filter = QComboBox()
        self._type_filter.addItem("Все типы", "")
        for key, label in MEDIA_TYPES.items():
            self._type_filter.addItem(label, key)
        self._type_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self._type_filter)

        self._status_filter = QComboBox()
        self._status_filter.addItem("Все статусы", "")
        for key, label in STATUSES.items():
            self._status_filter.addItem(label, key)
        self._status_filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self._status_filter)

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

        items = self._service.get_all()
        type_f   = self._type_filter.currentData()
        status_f = self._status_filter.currentData()
        if type_f:
            items = [i for i in items if i.media_type == type_f]
        if status_f:
            items = [i for i in items if i.status == status_f]

        if not items:
            empty = QLabel("Каталог пуст.\nНажмите «+ Добавить» чтобы начать.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; margin: 30px;")
            self._list_layout.insertWidget(0, empty)
            return

        for item in items:
            self._list_layout.insertWidget(self._list_layout.count() - 1, self._make_card(item))

    def _make_card(self, item: MediaItem) -> QWidget:
        card = QWidget()
        card.setObjectName("Card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)

        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        color_bar.setStyleSheet(f"background: {item.color}; border-radius: 2px; border: none;")
        layout.addWidget(color_bar)
        layout.addSpacing(8)

        info = QVBoxLayout()
        title_row = QHBoxLayout()
        title_lbl = QLabel(f"{item.type_label}  {item.title}")
        title_lbl.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 13px; font-weight: bold;")
        title_row.addWidget(title_lbl)
        status_lbl = QLabel(item.status_label)
        status_color = {"planned": TEXT_MUTED, "in_progress": ACCENT, "completed": SUCCESS}[item.status]
        status_lbl.setStyleSheet(
            f"color: {status_color}; font-size: 10px; "
            f"background: {status_color}22; border-radius: 3px; padding: 2px 6px;"
        )
        title_row.addWidget(status_lbl)
        title_row.addStretch()
        info.addLayout(title_row)

        star_widget = _StarRating(item.rating)
        info.addWidget(star_widget)

        if item.notes:
            notes_lbl = QLabel(item.notes[:80] + ("..." if len(item.notes) > 80 else ""))
            notes_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
            info.addWidget(notes_lbl)

        layout.addLayout(info, stretch=1)

        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(32, 32)
        edit_btn.setStyleSheet(f"color: {TEXT_MUTED}; border-color: {BORDER};")
        edit_btn.clicked.connect(lambda _, i=item: self._on_edit(i))
        layout.addWidget(edit_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(32, 32)
        del_btn.setStyleSheet(f"color: {ACCENT2}; border-color: {ACCENT2};")
        del_btn.clicked.connect(lambda _, iid=item.id, name=item.title: self._on_delete(iid, name))
        layout.addWidget(del_btn)

        return card


class _StatsTab(QWidget):
    """Вкладка статистики: счётчики, средние оценки, топ-5."""

    def __init__(self, service: MediaService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self._total_card     = self._make_stat_card("ВСЕГО ЗАПИСЕЙ", "0", ACCENT)
        self._completed_card = self._make_stat_card("ЗАВЕРШЕНО В ЭТОМ ГОДУ", "0", SUCCESS)
        self._avg_card       = self._make_stat_card("СРЕДНЯЯ ОЦЕНКА", "—", "#FFD700")
        cards_row.addWidget(self._total_card)
        cards_row.addWidget(self._completed_card)
        cards_row.addWidget(self._avg_card)
        layout.addLayout(cards_row)

        layout.addWidget(_Divider())

        top_lbl = QLabel("ТОП-5 ПО ОЦЕНКЕ")
        top_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(top_lbl)

        self._top_layout = QVBoxLayout()
        self._top_layout.setSpacing(6)
        layout.addLayout(self._top_layout)

        layout.addStretch()

    @staticmethod
    def _make_stat_card(label: str, value: str, color: str) -> QWidget:
        w = QWidget()
        w.setObjectName("Card")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 12, 16, 12)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 9px; letter-spacing: 1px;")
        layout.addWidget(lbl)
        val_lbl = QLabel(value)
        val_lbl.setObjectName("StatValue")
        val_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(val_lbl)
        return w

    def refresh(self) -> None:
        total = len(self._service.get_all())
        completed_year = self._service.completed_this_year()
        avg = self._service.average_rating()

        self._update_card_value(self._total_card, str(total))
        self._update_card_value(self._completed_card, str(completed_year))
        self._update_card_value(self._avg_card, f"{avg:.1f}/10" if avg else "—")

        while self._top_layout.count():
            item = self._top_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        top = self._service.top_rated(5)
        if not top:
            empty = QLabel("Пока нет оценённых записей")
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            self._top_layout.addWidget(empty)
            return

        for i, item in enumerate(top, 1):
            row = QWidget()
            row.setObjectName("Card")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)
            rank_lbl = QLabel(f"#{i}")
            rank_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 12px; font-weight: bold;")
            rank_lbl.setFixedWidth(30)
            row_layout.addWidget(rank_lbl)
            title_lbl = QLabel(f"{item.type_label}  {item.title}")
            title_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            row_layout.addWidget(title_lbl, stretch=1)
            star = _StarRating(item.rating)
            row_layout.addWidget(star)
            self._top_layout.addWidget(row)

    @staticmethod
    def _update_card_value(card: QWidget, value: str) -> None:
        for child in card.findChildren(QLabel):
            if child.objectName() == "StatValue":
                child.setText(value)
                break


class _ChartsTab(QWidget):
    """Вкладка с двумя donut-диаграммами: по типам и по статусам."""

    def __init__(self, service: MediaService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(24)

        left = QVBoxLayout()
        left_lbl = QLabel("ПО ТИПАМ")
        left_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        left.addWidget(left_lbl)
        self._type_chart = _DonutChart()
        left.addWidget(self._type_chart, stretch=1)
        self._type_legend = QVBoxLayout()
        left.addLayout(self._type_legend)
        layout.addLayout(left, stretch=1)

        right = QVBoxLayout()
        right_lbl = QLabel("ПО СТАТУСАМ")
        right_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        right.addWidget(right_lbl)
        self._status_chart = _DonutChart()
        right.addWidget(self._status_chart, stretch=1)
        self._status_legend = QVBoxLayout()
        right.addLayout(self._status_legend)
        layout.addLayout(right, stretch=1)

    def refresh(self) -> None:
        type_counts = self._service.count_by_type()
        type_labels = {MEDIA_TYPES[k]: v for k, v in type_counts.items()}
        self._type_chart.set_data(type_labels)
        self._fill_legend(self._type_legend, type_labels)

        status_counts = self._service.count_by_status()
        status_labels = {STATUSES[k]: v for k, v in status_counts.items()}
        self._status_chart.set_data(status_labels)
        self._fill_legend(self._status_legend, status_labels)

    @staticmethod
    def _fill_legend(layout: QVBoxLayout, data: dict[str, int]) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        filtered = {k: v for k, v in data.items() if v > 0}
        for i, (label, count) in enumerate(filtered.items()):
            color = _PIE_COLORS[i % len(_PIE_COLORS)]
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 12px;")
            dot.setFixedWidth(18)
            row_layout.addWidget(dot)
            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            row_layout.addWidget(name_lbl, stretch=1)
            count_lbl = QLabel(str(count))
            count_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            row_layout.addWidget(count_lbl)
            layout.addWidget(row)


class MediaView(QWidget):
    """Главный виджет медиатрекера с тремя вкладками."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = MediaService()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("MEDIA TRACKER")
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

        self._library_tab = _LibraryTab(
            self._service, on_add=self._on_add, on_edit=self._on_edit, on_delete=self._on_delete,
        )
        self._stats_tab  = _StatsTab(self._service)
        self._charts_tab = _ChartsTab(self._service)

        self._tabs.addTab(self._library_tab, "БИБЛИОТЕКА")
        self._tabs.addTab(self._stats_tab,   "СТАТИСТИКА")
        self._tabs.addTab(self._charts_tab,  "ДИАГРАММЫ")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        root.addWidget(self._tabs, stretch=1)

    def _on_tab_changed(self, index: int) -> None:
        match index:
            case 0: self._library_tab.refresh()
            case 1: self._stats_tab.refresh()
            case 2: self._charts_tab.refresh()

    def _on_data_changed(self) -> None:
        self._library_tab.refresh()
        self._stats_tab.refresh()
        self._charts_tab.refresh()

    def _on_add(self) -> None:
        dlg = _ItemDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                item = self._service.add_item(data["title"], data["media_type"], data["status"])
                if data["rating"] or data["notes"]:
                    self._service.edit_item(
                        item.id, data["title"], data["media_type"], data["status"],
                        data["rating"], data["notes"],
                    )
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_edit(self, item: MediaItem) -> None:
        dlg = _ItemDialog(self, item=item)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            try:
                self._service.edit_item(item.id, **data)
                self._on_data_changed()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _on_delete(self, item_id: str, name: str) -> None:
        reply = QMessageBox.question(
            self, "Удалить запись", f"Удалить «{name}» из каталога?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._service.delete_item(item_id)
            self._on_data_changed()

    def refresh(self) -> None:
        """Вызывается хуком on_activated."""
        self._library_tab.refresh()