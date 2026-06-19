from __future__ import annotations

import asyncio
import datetime
from typing import Any

import pyqtgraph as pg
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
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
    ACCENT, ACCENT2, BORDER, PLOT_BG, PLOT_FILL, PLOT_LINE, SUCCESS, TEXT, TEXT_MUTED,
)


class FetchWorker(QThread):
    """
    QThread для выполнения async-запросов к API ЦБ.
    """

    daily_ready:    pyqtSignal = pyqtSignal(object)
    history_ready:  pyqtSignal = pyqtSignal(object)
    error_occurred: pyqtSignal = pyqtSignal(str)

    def __init__(self, task: str, **kwargs: Any) -> None:
        super().__init__()
        self._task = task
        self._kwargs = kwargs

    def run(self) -> None:
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
            self.daily_ready.emit(parse_daily_rates(raw))  # type: ignore[attr-defined]
        except (CbrApiError, ProcessingError) as exc:
            self.error_occurred.emit(str(exc))  # type: ignore[attr-defined]

    async def _fetch_history(self) -> None:
        try:
            raw = await fetch_currency_history(
                currency_id=self._kwargs["currency_id"],
                date_from=self._kwargs["date_from"],
                date_to=self._kwargs["date_to"],
            )
            self.history_ready.emit(  # type: ignore[attr-defined]
                parse_currency_history(raw, self._kwargs["currency_id"])
            )
        except (CbrApiError, ProcessingError, ValueError) as exc:
            self.error_occurred.emit(str(exc))  # type: ignore[attr-defined]


class ChartWidget(QWidget):
    """
    pyqtgraph PlotWidget со стилизацией Sci-Fi Dark.
    Отображает историю курса (линия + заливка) или текущий курс (горизонтальная линия).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOptions(antialias=True, background=PLOT_BG, foreground=TEXT)
        self._plot = pg.PlotWidget()
        self._plot.setBackground(PLOT_BG)
        self._plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._style_axes()
        layout.addWidget(self._plot)

    def _style_axes(self) -> None:
        plot_item = self._plot.getPlotItem()
        assert plot_item is not None
        plot_item.showGrid(x=True, y=True, alpha=0.2)
        axis_pen = pg.mkPen(color=BORDER, width=1)
        label_style = {"color": TEXT_MUTED, "font-size": "11px"}
        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(color=TEXT_MUTED))
        plot_item.getAxis("left").setLabel("Курс (₽)", **label_style)
        plot_item.getAxis("bottom").setLabel("Дата", **label_style)
        plot_item.showAxis("top", False)
        plot_item.showAxis("right", False)

    def plot_history(self, history: HistoryData) -> None:
        """Отрисовывает исторические данные: линия тренда с заливкой под ней."""
        self._plot.clear()
        if not history.dates or not history.values:
            return

        ordinals: tuple[float, ...] = tuple(float(d.toordinal()) for d in history.dates)
        values: tuple[float, ...] = tuple(history.values)
        min_val = min(values)

        fill_color = QColor(PLOT_FILL[:-2])
        fill_color.setAlpha(30)

        baseline = pg.PlotDataItem(ordinals, (min_val,) * len(values))
        line = pg.PlotDataItem(
            ordinals, values,
            pen=pg.mkPen(color=PLOT_LINE, width=2.5),
            shadowPen=pg.mkPen(color=PLOT_LINE, width=6, alpha=40),
        )
        fill = pg.FillBetweenItem(line, baseline, brush=pg.mkBrush(fill_color))

        self._plot.addItem(fill)
        self._plot.addItem(line)

        scatter: pg.ScatterPlotItem | None = None
        if len(values) <= 30:
            scatter = pg.ScatterPlotItem(
                x=ordinals, y=values, size=6,
                pen=pg.mkPen(None), brush=pg.mkBrush(PLOT_LINE),
            )
            self._plot.addItem(scatter)

        nom_str = f"(за {history.nominal} ед.)" if history.nominal > 1 else ""
        self._plot.setTitle(
            f"<span style='color:{ACCENT}; font-family:Consolas; font-size:13px;'>"
            f"{history.currency_id} / RUB {nom_str}</span>"
        )

        plot_item = self._plot.getPlotItem()
        assert plot_item is not None
        plot_item.setAxisItems({"bottom": pg.DateAxisItem(orientation="bottom")})

        epoch = datetime.date(1970, 1, 1)
        unix_ts: tuple[float, ...] = tuple(
            (datetime.date.fromordinal(int(o)) - epoch).total_seconds()
            for o in ordinals
        )
        line.setData(unix_ts, values)
        baseline.setData(unix_ts, (min_val,) * len(values))
        if scatter is not None:
            scatter.setData(x=unix_ts, y=values)

        self._plot.getViewBox().setYRange(min_val * 0.995, max(values) * 1.005)

    def plot_single_rate(self, rate: CurrencyRate) -> None:
        """Отображает текущий курс горизонтальной пунктирной линией."""
        self._plot.clear()
        self._plot.setTitle(
            f"<span style='color:{ACCENT}; font-family:Consolas; font-size:13px;'>"
            f"Текущий курс {rate.currency_id} / RUB</span>"
        )
        value = rate.value
        self._plot.plot(
            list(range(10)), [value] * 10,
            pen=pg.mkPen(color=ACCENT2, width=3, style=Qt.PenStyle.DashLine),
        )
        self._plot.setYRange(value * 0.99, value * 1.01)

    def clear(self) -> None:
        self._plot.clear()
        self._plot.setTitle("")


class CurrencyView(QWidget):
    """
    Главный виджет трекера валют. Три секции:
      1. Панель управления — выбор валюты, режим, диапазон дат
      2. Строка статуса — название валюты, дата, текущий/итоговый курс
      3. График pyqtgraph
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: FetchWorker | None = None
        self._current_rates: dict[str, CurrencyRate] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(16)
        root_layout.addWidget(self._make_header())
        root_layout.addWidget(self._make_control_panel())
        root_layout.addWidget(self._make_status_bar())
        self._chart = ChartWidget()
        root_layout.addWidget(self._chart, stretch=1)

    @staticmethod
    def _make_header() -> QWidget:
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
        card = QWidget()
        card.setObjectName("Card")
        outer = QVBoxLayout(card)
        outer.setSpacing(12)
        outer.setContentsMargins(16, 14, 16, 14)

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

        self._date_row = QWidget()
        date_layout = QHBoxLayout(self._date_row)
        date_layout.setContentsMargins(0, 0, 0, 0)
        date_layout.setSpacing(16)

        date_label = QLabel("ПЕРИОД:")
        date_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        date_layout.addWidget(date_label)

        self._date_from = QDateEdit()
        self._date_from.setCalendarPopup(True)
        self._date_from.setDate(QDate.currentDate().addMonths(-3))
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
        self._mode_history.toggled.connect(self._date_row.setVisible)

        return card

    def _make_status_bar(self) -> QWidget:
        w = QWidget()
        w.setObjectName("Card")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(16, 10, 16, 10)
        self._status_label = QLabel("// ДАННЫЕ НЕ ЗАГРУЖЕНЫ — НАЖМИТЕ 'ЗАГРУЗИТЬ'")
        self._status_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(self._status_label)
        layout.addStretch()
        self._rate_label = QLabel("")
        self._rate_label.setStyleSheet(f"color: {ACCENT}; font-size: 20px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(self._rate_label)
        return w

    def _on_fetch_clicked(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return

        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("⟳  ЗАГРУЗКА...")
        self._status_label.setText("// CONNECTING TO CBR.RU...")
        self._rate_label.setText("")
        self._chart.clear()

        currency_id: str = self._currency_combo.currentData()

        if self._mode_current.isChecked():
            self._worker = FetchWorker("daily")
            self._worker.daily_ready.connect(self._on_daily_received)  # type: ignore[attr-defined]
        else:
            self._worker = FetchWorker(
                "history",
                currency_id=currency_id,
                date_from=self._date_from.date().toPyDate(),
                date_to=self._date_to.date().toPyDate(),
            )
            self._worker.history_ready.connect(self._on_history_received)  # type: ignore[attr-defined]

        self._worker.error_occurred.connect(self._on_error)  # type: ignore[attr-defined]
        self._worker.finished.connect(self._on_worker_finished)  # type: ignore[attr-defined]
        self._worker.start()

    def _on_daily_received(self, rates: dict[str, CurrencyRate]) -> None:
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
        if not history.dates:
            self._on_error("Нет данных за выбранный период")
            return

        change = history.values[-1] - history.values[0]
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
            f" <span style='color:{ACCENT};'>{history.values[-1]:.4f} ₽</span>"
        )
        self._rate_label.setTextFormat(Qt.TextFormat.RichText)
        self._chart.plot_history(history)

    def _on_error(self, message: str) -> None:
        self._status_label.setText(f"// ОШИБКА: {message}")
        self._status_label.setStyleSheet(f"color: {ACCENT2}; font-size: 11px; letter-spacing: 1px;")

    def _on_worker_finished(self) -> None:
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("▶  ЗАГРУЗИТЬ")
        self._worker = None

    def refresh(self) -> None:
        """Автообновление при переключении на модуль через хук on_activated."""
        if self._mode_current.isChecked() and not self._current_rates:
            self._on_fetch_clicked()