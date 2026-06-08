"""
modules/currency_tracker/logic/data_processor.py
=================================================
Бизнес-логика: парсинг, валидация и подготовка данных трекера валют.

Получает сырые XML-данные от API-слоя и возвращает
чистые структуры данных, готовые к отображению.

Зависимости: только стандартная библиотека + lxml.
Не импортирует ничего из UI-слоя (принцип Clean Architecture).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import NamedTuple

from lxml import etree

from modules.currency_tracker.api.cbr_client import CbrRawData


# ── Структуры данных ────────────────────────────────────────────────────────

class CurrencyRate(NamedTuple):
    """Курс одной валюты на одну дату."""
    currency_id: str       # Трёхбуквенный ISO-код: "USD"
    name: str              # Полное название: "Доллар США"
    value: float           # Курс в рублях (с учётом nominal)
    nominal: int           # Номинал (например 100 для JPY)
    rate_date: date        # Дата курса


@dataclass
class HistoryData:
    """Исторические данные курса для одной валюты."""
    currency_id: str
    name: str
    dates: list[date]       # Список дат (ось X)
    values: list[float]     # Список курсов (ось Y), aligned с dates
    nominal: int


class ProcessingError(Exception):
    """Ошибка при парсинге или обработке данных."""


# ── Функции парсинга ────────────────────────────────────────────────────────

def parse_daily_rates(raw: CbrRawData) -> dict[str, CurrencyRate]:
    """
    Парсит XML с дневными курсами всех валют.

    Возвращает словарь {ISO_код: CurrencyRate}.

    Пример XML-ответа ЦБ:
        <ValCurs Date="10.06.2024" name="Foreign Currency Market">
          <Valute ID="R01235">
            <NumCode>840</NumCode>
            <CharCode>USD</CharCode>
            <Nominal>1</Nominal>
            <Name>Доллар США</Name>
            <Value>87,1234</Value>
          </Valute>
          ...
        </ValCurs>
    """
    try:
        root = etree.fromstring(raw.xml_content)
    except etree.XMLSyntaxError as exc:
        raise ProcessingError(f"Ошибка парсинга XML: {exc}") from exc

    # Дата из атрибута корневого элемента
    date_str = root.get("Date", "")
    try:
        rate_date = _parse_cbr_date(date_str)
    except ValueError:
        rate_date = date.today()

    result: dict[str, CurrencyRate] = {}

    for valute in root.findall("Valute"):
        try:
            char_code = _text(valute, "CharCode")
            name = _text(valute, "Name")
            nominal = int(_text(valute, "Nominal"))
            # ЦБ возвращает числа с запятой: "87,1234"
            value_raw = _text(valute, "Value").replace(",", ".")
            # Нормализуем: приводим к курсу за 1 единицу
            value = float(value_raw) / nominal

            result[char_code] = CurrencyRate(
                currency_id=char_code,
                name=name,
                value=value,
                nominal=nominal,
                rate_date=rate_date,
            )
        except (ValueError, TypeError, AttributeError):
            # Пропускаем валюты с неполными данными
            continue

    if not result:
        raise ProcessingError("XML не содержит данных о курсах валют")

    return result


def parse_currency_history(raw: CbrRawData, currency_id: str) -> HistoryData:
    """
    Парсит XML с динамикой курса одной валюты.

    Пример XML-ответа ЦБ:
        <ValCurs ID="R01235" DateRange1="..." DateRange2="..." name="...">
          <Record Date="01.01.2024" Id="R01235">
            <Nominal>1</Nominal>
            <Value>88,1500</Value>
          </Record>
          ...
        </ValCurs>
    """
    try:
        root = etree.fromstring(raw.xml_content)
    except etree.XMLSyntaxError as exc:
        raise ProcessingError(f"Ошибка парсинга XML: {exc}") from exc

    name = root.get("name", currency_id)

    dates: list[date] = []
    values: list[float] = []
    nominal: int = 1

    for record in root.findall("Record"):
        try:
            date_str = record.get("Date", "")
            rate_date = _parse_cbr_date(date_str)

            nominal = int(_text(record, "Nominal"))
            value_raw = _text(record, "Value").replace(",", ".")
            value = float(value_raw) / nominal

            dates.append(rate_date)
            values.append(value)
        except (ValueError, TypeError, AttributeError):
            continue

    if not dates:
        raise ProcessingError(
            f"Нет данных о курсе {currency_id} за указанный период"
        )

    # Сортируем по дате (на случай неупорядоченных данных)
    paired = sorted(zip(dates, values), key=lambda x: x[0])
    dates, values = zip(*paired)  # type: ignore[assignment]

    return HistoryData(
        currency_id=currency_id,
        name=name,
        dates=list(dates),
        values=list(values),
        nominal=nominal,
    )


# ── Вспомогательные функции ─────────────────────────────────────────────────

def _text(element: etree._Element, tag: str) -> str:
    """Возвращает текст дочернего элемента или вызывает AttributeError."""
    child = element.find(tag)
    if child is None or child.text is None:
        raise AttributeError(f"Тег <{tag}> не найден или пуст")
    return child.text.strip()


def _parse_cbr_date(date_str: str) -> date:
    """Парсит дату в формате ЦБ РФ: 'DD.MM.YYYY'."""
    parts = date_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Неверный формат даты: {date_str!r}")
    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
    return date(year, month, day)