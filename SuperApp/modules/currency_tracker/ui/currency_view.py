"""
modules/currency_tracker/ui/currency_view.py
============================================
UI-слой: главный виджет трекера валют.

Архитектура асинхронности:
- Сетевые запросы выполняются в QThread (WorkerThread)
- Результаты передаются в UI-поток через сигналы Qt (потокобезопасно)
- UI никогда не блокируется

Компоненты:
- CurrencyView       — главный виджет (встраивается в NavigationManager)
- FetchWorker        — QThread для выполнения async запросов
- ChartWidget        — обёртка над pyqtgraph с кастомной Sci-Fi стилизацией
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

import pyqtgraph as pg
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from modules.currency_tracker.api.cbr_client import (
    CURRENCY_CODES,
    CbrApiError,
    fetch_currency_history,
    fetch_daily_rates,
)
from modules.currency_tracker.logic.data_processor import (
    CurrencyRate,
    HistoryData,
    ProcessingError,
    parse_currency_history,
    parse_daily_rates,
)
from ui.themes.scifi_dark import (
    ACCENT,
    ACCENT2,
    BG_DEEP,
    BG_ELEVATED,
    BG_SURFACE,
    BORDER,
    PLOT_BG,
    PLOT_FILL,
    PLOT_GRID,
    PLOT_LINE,
    SUCCESS,
    TEXT,
    TEXT_MUTED,
)


# ── Воркер для фоновых запросов ─────────────────────────────────────────────

class FetchWorker(QThread):
    """
    QThread, исполняющий async-функции httpx в отдельном потоке.

    Сигналы:
        daily_ready(dict)     — результат запроса дневных курсов
        history_ready(object) — результат запроса истории
        error_occurred(str)   — текст ошибки
    """

    daily_ready   = pyqtSignal(object)   # dict[str, CurrencyRate]
    history_ready = pyqtSignal(object)   # HistoryData
    error_occurred = pyqtSignal(str)

    def __init__(self, task: str, **kwargs: Any) -> None:
        super().__init__()
        self._task = task       # "daily" | "history"
        self._kwargs = kwargs

    def run(self) -> None:
        """Запускается в отдельном потоке."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if self._task == "daily":
                loop.run_until_complete(self._fetch_daily())
            elif self._task == "history":
                loop.run_until_complete(self._fetch_history())
        finally:
            loop.close()

    async def _fetch_daily(self) -> None:
        try:
            raw = await fetch_daily_rates()
            rates = parse_daily_rates(raw)
            self.daily_ready.emit(rates)
        except (CbrApiError, ProcessingError) as exc:
            self.error_occurred.emit(str(exc))

    async def _fetch_history(self) -> None:
        try:
            raw = await fetch_currency_history(
                currency_id=self._kwargs["currency_id"],
                date_from=self._kwargs["date_from"],
                date_to=self._kwargs["date_to"],
            )
            history = parse_currency_history(raw, self._kwargs["currency_id"])
            self.history_ready.emit(history)
        except (CbrApiError, ProcessingError, ValueError) as exc:
            self.error_occurred.emit(str(exc))


# ── График ──────────────────────────────────────────────────────────────────

class ChartWidget(QWidget):
    """
    Обёртка над pyqtgraph PlotWidget с Sci-Fi стилизацией.

    Методы:
        plot_history(history)  — отрисовывает исторические данные
        clear()                — очищает график
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Настройка pyqtgraph — тёмный фон
        pg.setConfigOptions(antialias=True, background=PLOT_BG, foreground=TEXT)

        self._plot = pg.PlotWidget()
        self._plot.setBackground(PLOT_BG)
        self._plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Стилизация осей
        self._style_axes()

        layout.addWidget(self._plot)

    def _style_axes(self) -> None:
        """Применяет Sci-Fi стилизацию к осям графика."""
        plot_item = self._plot.getPlotItem()
        assert plot_item is not None

        # Включаем сетку
        plot_item.showGrid(x=True, y=True, alpha=0.2)

        # Стиль подписей осей
        axis_pen = pg.mkPen(color=BORDER, width=1)
        label_style = {"color": TEXT_MUTED, "font-size": "11px"}

        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=TEXT_MUTED))
            axis.label.setFont

        plot_item.getAxis("left").setLabel("Курс (₽)", **label_style)
        plot_item.getAxis("bottom").setLabel("Дата", **label_style)

        # Скрыть верхнюю и правую оси
        plot_item.showAxis("top", False)
        plot_item.showAxis("right", False)

    def plot_history(self, history: HistoryData) -> None:
        """Отрисовывает исторические данные курса."""
        self._plot.clear()

        if not history.dates or not history.values:
            return

        # Конвертируем даты в числа (Unix timestamp) для pyqtgraph
        timestamps = [
            float(d.toordinal()) for d in history.dates
        ]
        values = history.values

        # ── Заливка под графиком ──────────────────────────────────────────
        fill_color = QColor(PLOT_FILL[:-2])  # убираем alpha из hex
        fill_color.setAlpha(30)
        fill_brush = pg.mkBrush(fill_color)

        # Линия + заливка (FillBetweenItem)
        baseline = pg.PlotDataItem(timestamps, [min(values)] * len(values))
        line = pg.PlotDataItem(
            timestamps,
            values,
            pen=pg.mkPen(color=PLOT_LINE, width=2.5),
            shadowPen=pg.mkPen(color=PLOT_LINE, width=6, alpha=40),
        )
        fill = pg.FillBetweenItem(line, baseline, brush=fill_brush)

        self._plot.addItem(fill)
        self._plot.addItem(line)

        # ── Точки на узлах ────────────────────────────────────────────────
        # Показываем точки только если данных немного (курс за неделю)
        if len(values) <= 30:
            scatter = pg.ScatterPlotItem(
                x=timestamps,
                y=values,
                size=6,
                pen=pg.mkPen(None),
                brush=pg.mkBrush(PLOT_LINE),
            )
            self._plot.addItem(scatter)

        # ── Заголовок графика ─────────────────────────────────────────────
        nom_str = f"(за {history.nominal} ед.)" if history.nominal > 1 else ""
        self._plot.setTitle(
            f"<span style='color:{ACCENT}; font-family:Consolas; font-size:13px;'>"
            f"{history.currency_id} / RUB {nom_str}"
            f"</span>",
        )

        # ── Кастомная ось X (даты) ────────────────────────────────────────
        date_axis = pg.DateAxisItem(orientation="bottom")
        # Заменяем ось X на DateAxis
        plot_item = self._plot.getPlotItem()
        assert plot_item is not None
        plot_item.setAxisItems({"bottom": date_axis})

        # Конвертируем ordinal → timestamp для DateAxisItem
        import datetime
        unix_timestamps = [
            (datetime.date.fromordinal(int(t)) - datetime.date(1970, 1, 1)).total_seconds()
            for t in timestamps
        ]
        line.setData(unix_timestamps, values)
        baseline.setData(unix_timestamps, [min(values)] * len(values))
        if len(values) <= 30:
            scatter.setData(x=unix_timestamps, y=values)

        # Авто-масштаб с небольшим отступом
        self._plot.getViewBox().setYRange(
            min(values) * 0.995,
            max(values) * 1.005,
        )

    def plot_single_rate(self, rate: CurrencyRate) -> None:
        """Показывает текущий курс в виде горизонтальной линии (baseline)."""
        self._plot.clear()
        self._plot.setTitle(
            f"<span style='color:{ACCENT}; font-family:Consolas; font-size:13px;'>"
            f"Текущий курс {rate.currency_id} / RUB"
            f"</span>"
        )
        # Рисуем горизонтальную линию ± небольшой диапазон для визуализации
        value = rate.value
        x = list(range(10))
        y = [value] * 10
        self._plot.plot(
            x, y,
            pen=pg.mkPen(color=ACCENT2, width=3, style=Qt.PenStyle.DashLine),
        )
        self._plot.setYRange(value * 0.99, value * 1.01)

    def clear(self) -> None:
        self._plot.clear()
        self._plot.setTitle("")


# ── Главный виджет модуля ───────────────────────────────────────────────────

class CurrencyView(QWidget):
    """
    Главный виджет трекера валют.

    Три секции:
    1. Панель управления: выбор валюты, режим, даты, кнопка обновления
    2. Панель статуса: текущий курс + метаданные
    3. График
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: FetchWorker | None = None
        self._current_rates: dict[str, CurrencyRate] = {}
        self._build_ui()

    # ── Построение UI ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(16)

        # Заголовок модуля
        root_layout.addWidget(self._make_header())

        # Панель управления
        root_layout.addWidget(self._make_control_panel())

        # Строка статуса / текущий курс
        root_layout.addWidget(self._make_status_bar())

        # График
        self._chart = ChartWidget()
        root_layout.addWidget(self._chart, stretch=1)

    def _make_header(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("CURRENCY TRACKER")
        title.setObjectName("ModuleTitle")
        layout.addWidget(title)

        layout.addStretch()

        subtitle = QLabel("// ЦБ РФ FEED")
        subtitle.setObjectName("ModuleSubtitle")
        layout.addWidget(subtitle)

        return w

    def _make_control_panel(self) -> QWidget:
        """Панель с контролами — обёрнута в Card."""
        card = QWidget()
        card.setObjectName("Card")
        outer = QVBoxLayout(card)
        outer.setSpacing(12)
        outer.setContentsMargins(16, 14, 16, 14)

        # ── Строка 1: Выбор валюты + режим ───────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(16)

        currency_label = QLabel("ВАЛЮТА:")
        currency_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        row1.addWidget(currency_label)

        self._currency_combo = QComboBox()
        for code in CURRENCY_CODES:
            self._currency_combo.addItem(code, code)
        row1.addWidget(self._currency_combo)

        row1.addSpacing(24)

        mode_label = QLabel("РЕЖИМ:")
        mode_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        row1.addWidget(mode_label)

        self._mode_current = QRadioButton("Текущий курс")
        self._mode_history = QRadioButton("История")
        self._mode_current.setChecked(True)
        row1.addWidget(self._mode_current)
        row1.addWidget(self._mode_history)

        row1.addStretch()

        self._refresh_btn = QPushButton("▶  ЗАГРУЗИТЬ")
        self._refresh_btn.setFixedWidth(160)
        self._refresh_btn.clicked.connect(self._on_fetch_clicked)
        row1.addWidget(self._refresh_btn)

        outer.addLayout(row1)

        # ── Строка 2: Даты (показывается только в режиме история) ─────────
        self._date_row = QWidget()
        date_layout = QHBoxLayout(self._date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(16)

        date_label = QLabel("ПЕРИОД:")
        date_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        date_layout.addWidget(date_label)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        default_from = QDate.currentDate().addMonths(-3)
        self._date_from.setDate(default_from)
        self._date_from.setDisplayFormat("dd.MM.yyyy")
        date_layout.addWidget(self._date_from)

        dash = QLabel("—")
        dash.setStyleSheet(f"color: {TEXT_MUTED};")
        date_layout.addWidget(dash)

        self._date_to = QDateEdit()
        self._date_to.setCalendarPopup(True)
        self._date_to.setDate(QDate.currentDate())
        self._date_to.setDisplayFormat("dd.MM.yyyy")
        date_layout.addWidget(self._date_to)

        date_layout.addStretch()
        outer.addWidget(self._date_row)
        self._date_row.setVisible(False)

        # Переключение видимости дат при смене режима
        self._mode_history.toggled.connect(self._date_row.setVisible)

        return card

    def _make_status_bar(self) -> QWidget:
        """Строка с текущим курсом."""
        w = QWidget()
        w.setObjectName("Card")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 10, 16, 10)

        self._status_label = QLabel("// ДАННЫЕ НЕ ЗАГРУЖЕНЫ — НАЖМИТЕ 'ЗАГРУЗИТЬ'")
        self._status_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;"
        )
        layout.addWidget(self._status_label)
        layout.addStretch()

        self._rate_label = QLabel("")
        self._rate_label.setStyleSheet(
            f"color: {ACCENT}; font-size: 20px; font-weight: bold; letter-spacing: 2px;"
        )
        layout.addWidget(self._rate_label)

        return w

    # ── Обработчики событий ──────────────────────────────────────────────────

    def _on_fetch_clicked(self) -> None:
        """Запускает загрузку данных в фоновом потоке."""
        if self._worker is not None and self._worker.isRunning():
            return  # Запрос уже выполняется

        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⟳  ЗАГРУЗКА...")
        self._status_label.setText("// CONNECTING TO CBR.RU...")
        self._rate_label.setText("")
        self._chart.clear()

        currency_id: str = self._currency_combo.currentData()

        if self._mode_current.isChecked():
            self._worker = FetchWorker("daily")
            self._worker.daily_ready.connect(self._on_daily_received)
        else:
            date_from = self._date_from.date().toPyDate()
            date_to   = self._date_to.date().toPyDate()
            self._worker = FetchWorker(
                "history",
                currency_id=currency_id,
                date_from=date_from,
                date_to=date_to,
            )
            self._worker.history_ready.connect(self._on_history_received)

        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_daily_received(self, rates: dict[str, CurrencyRate]) -> None:
        """Обрабатывает полученные дневные курсы."""
        self._current_rates = rates
        currency_id: str = self._currency_combo.currentData()

        if currency_id not in rates:
            self._on_error(f"Курс {currency_id} не найден в ответе ЦБ")
            return

        rate = rates[currency_id]
        nom_str = f" / {rate.nominal} ед." if rate.nominal > 1 else ""
        self._status_label.setText(
            f"// {rate.name}  ·  Дата: {rate.rate_date.strftime('%d.%m.%Y')}{nom_str}"
        )
        self._rate_label.setText(f"{rate.value:.4f} ₽")
        self._chart.plot_single_rate(rate)

    def _on_history_received(self, history: HistoryData) -> None:
        """Обрабатывает полученную историю курса."""
        if not history.dates:
            self._on_error("Нет данных за выбранный период")
            return

        last_value = history.values[-1]
        first_value = history.values[0]
        change = last_value - first_value
        sign = "▲" if change >= 0 else "▼"
        color = SUCCESS if change >= 0 else ACCENT2

        self._status_label.setText(
            f"// {history.name}  ·  "
            f"Период: {history.dates[0].strftime('%d.%m.%Y')} — "
            f"{history.dates[-1].strftime('%d.%m.%Y')}  ·  "
            f"Точек: {len(history.dates)}"
        )
        self._rate_label.setText(
            f"<span style='color:{color};'>{sign} {abs(change):.4f}</span>"
            f" <span style='color:{ACCENT};'>{last_value:.4f} ₽</span>"
        )
        self._rate_label.setTextFormat(Qt.TextFormat.RichText)
        self._chart.plot_history(history)

    def _on_error(self, message: str) -> None:
        """Отображает ошибку."""
        self._status_label.setText(f"// ОШИБКА: {message}")
        self._status_label.setStyleSheet(
            f"color: {ACCENT2}; font-size: 11px; letter-spacing: 1px;"
        )

    def _on_worker_finished(self) -> None:
        """Восстанавливает кнопку после завершения запроса."""
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("▶  ЗАГРУЗИТЬ")
        self._worker = None

    def refresh(self) -> None:
        """Публичный метод: обновить данные (вызывается хуком on_activated)."""
        # Автоматически обновляем текущий курс при переключении на модуль
        if self._mode_current.isChecked() and not self._current_rates:
            self._on_fetch_clicked()