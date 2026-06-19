from __future__ import annotations


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from modules.budget_tracker.logic.service import BudgetService, Goal
from ui.themes.scifi_dark import (
    ACCENT, ACCENT2, BG_DEEP, BG_ELEVATED, BG_SURFACE,
    BORDER, SUCCESS, TEXT, TEXT_MUTED, TEXT_BRIGHT,
)

# Палитра для секторов круговой диаграммы
_PIE_COLORS = [
    "#00D4FF", "#FF6B35", "#39FF14", "#FFD700", "#FF69B4",
    "#A855F7", "#06B6D4", "#F97316", "#84CC16", "#EC4899",
]

_ICON_OPTIONS = ["🎯", "🏠", "🚗", "✈️", "💻", "📱", "💍", "🎓", "💪", "🌴"]

class _Divider(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet(f"background-color: {BORDER}; max-height: 1px; border: none;")


class _StatCard(QWidget):
    """Карточка с одним числовым показателем."""

    def __init__(self, label: str, value: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(lbl)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold; letter-spacing: 1px;"
        )
        layout.addWidget(self._value_label)

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)

    def set_color(self, color: str) -> None:
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold;"
        )


class _ProgressBar(QWidget):
    """Кастомный прогресс-бар в стиле Sci-Fi."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(8)
        self._pct = 0.0

    def set_percent(self, pct: float) -> None:
        self._pct = max(0.0, min(100.0, pct))
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Фон
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BORDER)))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)

        # Заливка
        if self._pct > 0:
            fill_w = int(self.width() * self._pct / 100)
            color = SUCCESS if self._pct >= 100 else ACCENT
            painter.setBrush(QBrush(QColor(color)))
            painter.drawRoundedRect(0, 0, fill_w, self.height(), 4, 4)

        painter.end()


class _PieChartWidget(QWidget):
    """
    Круговая диаграмма расходов по категориям.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data: dict[str, float] = {}
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, data: dict[str, float]) -> None:
        self._data = data
        self.update()

    def paintEvent(self, event: object) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 40
        x = (w - size) // 2
        y = (h - size) // 2

        if not self._data:
            painter.setPen(QColor(TEXT_MUTED))
            painter.setFont(QFont("Consolas", 11))
            painter.drawText(
                0, 0, w, h,
                Qt.AlignmentFlag.AlignCenter,
                "Нет расходов за текущий месяц"
            )
            painter.end()
            return

        total = sum(self._data.values())
        start_angle = 90 * 16  # начинаем с 12 часов (Qt: единицы — 1/16 градуса)

        for i, (category, amount) in enumerate(self._data.items()):
            span = int(amount / total * 360 * 16)
            color = QColor(_PIE_COLORS[i % len(_PIE_COLORS)])

            painter.setPen(QPen(QColor(BG_DEEP), 2))
            painter.setBrush(QBrush(color))
            painter.drawPie(x, y, size, size, start_angle, span)
            start_angle += span

        # Центральный круг (эффект «donut»)
        inner = int(size * 0.42)
        ix = (w - inner) // 2
        iy = (h - inner) // 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(BG_DEEP)))
        painter.drawEllipse(ix, iy, inner, inner)

        # Сумма в центре
        painter.setPen(QColor(TEXT_BRIGHT))
        painter.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
        painter.drawText(
            ix, iy, inner, inner,
            Qt.AlignmentFlag.AlignCenter,
            f"{total:,.0f} ₽"
        )

        painter.end()


class _AddCategoryDialog(QDialog):
    """Диалог добавления пользовательской категории."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новая категория")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Спорт")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Тип:"))
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("📉  Расход", "expense")
        self.kind_combo.addItem("📈  Доход",  "income")
        layout.addWidget(self.kind_combo)

        layout.addWidget(QLabel("Иконка:"))
        self.icon_combo = QComboBox()
        icons = ["📦", "🎮", "🏋️", "🐾", "🎨", "🛠️", "🌿", "🎵", "✈️", "💰"]
        for icon in icons:
            self.icon_combo.addItem(icon, icon)
        layout.addWidget(self.icon_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, str, str]:
        return self.name_edit.text().strip(), self.icon_combo.currentData(), self.kind_combo.currentData()


class _AddGoalDialog(QDialog):
    """Диалог добавления цели накопления."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новая цель")
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Название цели:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Новый ноутбук")
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Целевая сумма (₽):"))
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(1, 100_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSingleStep(1000)
        self.amount_spin.setValue(10000)
        layout.addWidget(self.amount_spin)

        layout.addWidget(QLabel("Иконка:"))
        self.icon_combo = QComboBox()
        for icon in _ICON_OPTIONS:
            self.icon_combo.addItem(icon, icon)
        layout.addWidget(self.icon_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self) -> tuple[str, float, str]:
        return (
            self.name_edit.text().strip(),
            self.amount_spin.value(),
            self.icon_combo.currentData(),
        )

class _OverviewTab(QWidget):
    """Вкладка «Обзор»: баланс, сводка, последние 10 транзакций."""

    delete_requested = pyqtSignal(str)  # tx_id

    def __init__(self, service: BudgetService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(16)

        # Три карточки со статистикой
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._balance_card  = _StatCard("БАЛАНС",  "0.00 ₽", ACCENT)
        self._income_card   = _StatCard("ДОХОДЫ",  "0.00 ₽", SUCCESS)
        self._expense_card  = _StatCard("РАСХОДЫ", "0.00 ₽", ACCENT2)
        for card in (self._balance_card, self._income_card, self._expense_card):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        # Заголовок списка
        header = QHBoxLayout()
        lbl = QLabel("ПОСЛЕДНИЕ ТРАНЗАКЦИИ")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        header.addWidget(lbl)
        header.addStretch()
        layout.addLayout(header)

        layout.addWidget(_Divider())

        # Список транзакций
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_SURFACE};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {BORDER};
                color: {TEXT};
                font-family: Consolas;
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background-color: {BG_ELEVATED};
            }}
            QListWidget::item:hover {{
                background-color: {BG_ELEVATED};
            }}
        """)
        layout.addWidget(self._list, stretch=1)

        # Кнопка удаления выбранной
        del_btn = QPushButton("✕  Удалить выбранную")
        del_btn.clicked.connect(self._on_delete)
        del_btn.setStyleSheet(
            f"border-color: {ACCENT2}; color: {ACCENT2};"
            f"QPushButton:hover {{ background-color: {ACCENT2}; color: {BG_DEEP}; }}"
        )
        layout.addWidget(del_btn)

    def refresh(self) -> None:
        """Перезагружает все данные из сервиса."""
        balance  = self._service.get_balance()
        income   = self._service.get_total_income()
        expenses = self._service.get_total_expenses()

        b_color = SUCCESS if balance >= 0 else ACCENT2
        self._balance_card.set_value(f"{balance:+,.2f} ₽")
        self._balance_card.set_color(b_color)
        self._income_card.set_value(f"{income:,.2f} ₽")
        self._expense_card.set_value(f"{expenses:,.2f} ₽")

        self._list.clear()
        for tx in self._service.get_recent_transactions(10):
            sign   = "+" if tx.kind == "income" else "−"
            color  = SUCCESS if tx.kind == "income" else ACCENT2
            note   = f"  // {tx.note}" if tx.note else ""
            text   = (
                f"{tx.tx_date}   {tx.category:<20}"
                f"  {sign}{tx.amount:>10,.2f} ₽{note}"
            )
            item = QListWidgetItem(text)
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, tx.id)
            self._list.addItem(item)
        self._list.update()

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        tx_id = item.data(Qt.ItemDataRole.UserRole)
        if tx_id:
            self.delete_requested.emit(tx_id)


class _AddTransactionTab(QWidget):
    """Вкладка «Добавить»: форма новой транзакции."""

    transaction_added = pyqtSignal()
    category_added    = pyqtSignal()

    def __init__(self, service: BudgetService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 12, 0, 0)
        outer.setSpacing(0)

        # Форма в карточке
        card = QWidget()
        card.setObjectName("Card")
        card.setMaximumWidth(520)
        layout = QVBoxLayout(card)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Тип
        type_label = QLabel("ТИП")
        type_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(type_label)

        self._kind_combo = QComboBox()
        self._kind_combo.addItem("📈  Доход",  "income")
        self._kind_combo.addItem("📉  Расход", "expense")
        self._kind_combo.currentIndexChanged.connect(lambda _: self._refresh_categories())
        layout.addWidget(self._kind_combo)

        layout.addWidget(_Divider())

        # Сумма
        amount_label = QLabel("СУММА (₽)")
        amount_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(amount_label)

        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(0.01, 100_000_000)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setSingleStep(100)
        self._amount_spin.setValue(1000)
        layout.addWidget(self._amount_spin)

        layout.addWidget(_Divider())

        # Категория
        cat_label = QLabel("КАТЕГОРИЯ")
        cat_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(cat_label)

        cat_row = QHBoxLayout()
        self._cat_combo = QComboBox()
        cat_row.addWidget(self._cat_combo, stretch=1)
        add_cat_btn = QPushButton("+")
        add_cat_btn.setFixedWidth(36)
        add_cat_btn.setToolTip("Создать категорию")
        add_cat_btn.clicked.connect(self._on_add_category)
        cat_row.addWidget(add_cat_btn)
        layout.addLayout(cat_row)

        layout.addWidget(_Divider())

        # Заметка
        note_label = QLabel("ЗАМЕТКА (необязательно)")
        note_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        layout.addWidget(note_label)

        self._note_edit = QLineEdit()
        self._note_edit.setPlaceholderText("Например: супермаркет Пятёрочка")
        layout.addWidget(self._note_edit)

        layout.addSpacing(8)

        # Кнопка подтверждения
        self._submit_btn = QPushButton("✓  СОХРАНИТЬ ТРАНЗАКЦИЮ")
        self._submit_btn.setFixedHeight(40)
        self._submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self._submit_btn)

        # Сообщение об ошибке
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

        outer.addWidget(card)
        outer.addStretch()

        self._refresh_categories()

    def _refresh_categories(self) -> None:
        kind = self._kind_combo.currentData() or "expense"
        self._cat_combo.clear()
        for cat in self._service.get_categories(kind):
            self._cat_combo.addItem(f"{cat.icon}  {cat.name}", cat.name)

    def _on_add_category(self) -> None:
        dlg = _AddCategoryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, icon, kind = dlg.get_data()
            try:
                self._service.add_category(name, icon, kind)
                self._refresh_categories()
                self.category_added.emit()
                self._error_label.setText("")
            except ValueError as e:
                self._error_label.setText(str(e))

    def _on_submit(self) -> None:
        self._error_label.setText("")
        kind    = self._kind_combo.currentData()
        amount  = self._amount_spin.value()
        category = self._cat_combo.currentData()
        note    = self._note_edit.text().strip()

        if not category:
            self._error_label.setText("Выберите категорию")
            return

        try:
            self._service.add_transaction(kind, amount, category, note)
            self._note_edit.clear()
            self._amount_spin.setValue(1000)
            self.transaction_added.emit()
            self._error_label.setStyleSheet(f"color: {SUCCESS}; font-size: 11px;")
            self._error_label.setText("✓ Транзакция сохранена")
        except ValueError as e:
            self._error_label.setStyleSheet(f"color: {ACCENT2}; font-size: 11px;")
            self._error_label.setText(str(e))

    def refresh(self) -> None:
        self._refresh_categories()


class _ChartTab(QWidget):
    """Вкладка «Диаграмма»: круговой график расходов по категориям за текущий месяц."""

    def __init__(self, service: BudgetService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(24)

        # Диаграмма слева
        self._pie = _PieChartWidget()
        layout.addWidget(self._pie, stretch=3)

        # Легенда справа
        right = QVBoxLayout()
        right.setSpacing(8)

        month_label = QLabel("РАСХОДЫ ЗА МЕСЯЦ")
        month_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        right.addWidget(month_label)
        right.addWidget(_Divider())

        self._legend_widget = QWidget()
        self._legend_layout = QVBoxLayout(self._legend_widget)
        self._legend_layout.setSpacing(8)
        self._legend_layout.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self._legend_widget)
        right.addStretch()

        layout.addLayout(right, stretch=2)

    def refresh(self) -> None:
        data = self._service.get_expenses_by_category_this_month()
        self._pie.set_data(data)

        # Перестраиваем легенду
        while self._legend_layout.count():
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        total = sum(data.values()) or 1
        for i, (cat, amt) in enumerate(data.items()):
            color = _PIE_COLORS[i % len(_PIE_COLORS)]
            row = QHBoxLayout()

            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14px;")
            dot.setFixedWidth(20)
            row.addWidget(dot)

            name_lbl = QLabel(cat)
            name_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
            row.addWidget(name_lbl, stretch=1)

            pct = amt / total * 100
            pct_lbl = QLabel(f"{pct:.1f}%")
            pct_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
            row.addWidget(pct_lbl)

            amt_lbl = QLabel(f"{amt:,.0f} ₽")
            amt_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            amt_lbl.setMinimumWidth(90)
            amt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(amt_lbl)

            container = QWidget()
            container.setLayout(row)
            self._legend_layout.addWidget(container)


class _GoalsTab(QWidget):
    """Вкладка «Цели»: список целей накопления с прогресс-барами."""

    def __init__(self, service: BudgetService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        # Кнопка добавления
        top_row = QHBoxLayout()
        lbl = QLabel("ЦЕЛИ НАКОПЛЕНИЙ")
        lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px; letter-spacing: 2px;")
        top_row.addWidget(lbl)
        top_row.addStretch()
        add_btn = QPushButton("+ Новая цель")
        add_btn.clicked.connect(self._on_add_goal)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        layout.addWidget(_Divider())

        # Прокручиваемый список целей
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._goals_container = QWidget()
        self._goals_layout = QVBoxLayout(self._goals_container)
        self._goals_layout.setSpacing(10)
        self._goals_layout.setContentsMargins(0, 0, 0, 0)
        self._goals_layout.addStretch()

        scroll.setWidget(self._goals_container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self) -> None:
        # Очищаем список (кроме stretch)
        while self._goals_layout.count() > 1:
            item = self._goals_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        goals = self._service.get_goals()
        if not goals:
            empty = QLabel("Целей пока нет.\nНажмите «+ Новая цель» чтобы добавить первую.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px;")
            self._goals_layout.insertWidget(0, empty)
            return

        for goal in goals:
            self._goals_layout.insertWidget(
                self._goals_layout.count() - 1,
                self._make_goal_card(goal),
            )

    def _make_goal_card(self, goal: Goal) -> QWidget:
        card = QWidget()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 14, 16, 14)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel(f"{goal.icon}  {goal.name}")
        title.setStyleSheet(f"color: {TEXT_BRIGHT}; font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        pct_label = QLabel(f"{goal.progress_pct:.1f}%")
        color = SUCCESS if goal.progress_pct >= 100 else ACCENT
        pct_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        header.addWidget(pct_label)
        layout.addLayout(header)

        # Прогресс-бар
        bar = _ProgressBar()
        bar.set_percent(goal.progress_pct)
        layout.addWidget(bar)

        # Суммы
        amounts = QHBoxLayout()
        saved_lbl = QLabel(f"Накоплено: {goal.saved:,.2f} ₽")
        saved_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        amounts.addWidget(saved_lbl)
        amounts.addStretch()
        remain_lbl = QLabel(f"Осталось: {goal.remaining:,.2f} ₽")
        remain_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        amounts.addWidget(remain_lbl)
        layout.addLayout(amounts)

        # Кнопки
        btn_row = QHBoxLayout()
        deposit_btn = QPushButton("＋ Пополнить")
        deposit_btn.clicked.connect(lambda _, g=goal: self._on_deposit(g))
        btn_row.addWidget(deposit_btn)
        btn_row.addStretch()
        del_btn = QPushButton("✕ Удалить")
        del_btn.setStyleSheet(f"border-color: {ACCENT2}; color: {ACCENT2};")
        del_btn.clicked.connect(lambda _, gid=goal.id: self._on_delete(gid))
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        return card

    def _on_add_goal(self) -> None:
        dlg = _AddGoalDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, target, icon = dlg.get_data()
            try:
                self._service.add_goal(name, target, icon)
                self.refresh()
            except ValueError:
                pass

    def _on_deposit(self, goal: Goal) -> None:
        """Открывает диалог пополнения цели."""
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Пополнить: {goal.name}")
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        layout.addWidget(QLabel(f"Текущий прогресс: {goal.saved:,.2f} / {goal.target:,.2f} ₽"))

        spin = QDoubleSpinBox()
        spin.setRange(0.01, 100_000_000)
        spin.setDecimals(2)
        spin.setSingleStep(500)
        spin.setValue(1000)
        layout.addWidget(spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  # type: ignore[arg-type]
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self._service.add_to_goal(goal.id, spin.value())
                self.refresh()
            except ValueError:
                pass

    def _on_delete(self, goal_id: str) -> None:
        self._service.delete_goal(goal_id)
        self.refresh()


class BudgetView(QWidget):
    """
    Главный виджет модуля Budget Tracker.
    Содержит QTabWidget с четырьмя вкладками.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = BudgetService()
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel("BUDGET TRACKER")
        title.setObjectName("ModuleTitle")
        header.addWidget(title)
        header.addStretch()
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
            QTabBar::tab:hover {{
                color: {TEXT};
            }}
        """)

        self._overview_tab = _OverviewTab(self._service)
        self._overview_tab.delete_requested.connect(self._on_delete_transaction)

        self._add_tab = _AddTransactionTab(self._service)
        self._add_tab.transaction_added.connect(self._on_data_changed)
        self._add_tab.category_added.connect(self._on_data_changed)

        self._chart_tab = _ChartTab(self._service)
        self._goals_tab = _GoalsTab(self._service)

        self._tabs.addTab(self._overview_tab, "ОБЗОР")
        self._tabs.addTab(self._add_tab,      "ДОБАВИТЬ")
        self._tabs.addTab(self._chart_tab,    "ДИАГРАММА")
        self._tabs.addTab(self._goals_tab,    "ЦЕЛИ")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs, stretch=1)

    def _on_tab_changed(self, index: int) -> None:
        match index:
            case 0: self._overview_tab.refresh()
            case 1: self._add_tab.refresh()
            case 2: self._chart_tab.refresh()
            case 3: self._goals_tab.refresh()

    def _on_data_changed(self) -> None:
        # Всегда перезагружаем список явно — не полагаемся на currentChanged,
        # который не срабатывает если вкладка уже активна
        self._overview_tab.refresh()
        if self._tabs.currentIndex() != 0:
            self._tabs.setCurrentIndex(0)

    def _on_delete_transaction(self, tx_id: str) -> None:
        self._service.delete_transaction(tx_id)
        self._overview_tab.refresh()

    def refresh(self) -> None:
        """Вызывается хуком on_activated при переключении на модуль."""
        self._overview_tab.refresh()