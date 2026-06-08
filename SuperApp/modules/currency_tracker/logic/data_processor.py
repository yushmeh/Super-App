"""
modules/currency_tracker/logic/data_processor.py
=================================================
Бизнес-логика трекера валют: парсинг XML, валидация, подготовка данных для графика.
Получает CbrRawData от API-слоя, возвращает типизированные структуры.
Не импортирует ничего из UI-слоя.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, NamedTuple

from lxml import etree

from modules.currency_tracker.api.cbr_client import CbrRawData


class CurrencyRate(NamedTuple):
    """Курс одной валюты на одну дату."""
    currency_id: str   # ISO-код: "USD"
    name: str          # Полное название: "Доллар США"
    value: float       # Курс в рублях за 1 единицу (нормализован по nominal)
    nominal: int       # Исходный номинал из ответа ЦБ
    rate_date: date


@dataclass
class HistoryData:
    """Исторические данные курса для построения графика."""
    currency_id: str
    name: str
    dates: list[date]    # Ось X
    values: list[float]  # Ось Y, выровнена с dates
    nominal: int


class ProcessingError(Exception):
    """Ошибка парсинга или обработки данных."""


def parse_daily_rates(raw: CbrRawData) -> dict[str, CurrencyRate]:
    """
    Парсит XML с дневными курсами всех валют.
    Возвращает словарь {ISO_код: CurrencyRate}.

    Формат XML-ответа ЦБ:
        <ValCurs Date="10.06.2024">
          <Valute ID="R01235">
            <CharCode>USD</CharCode>
            <Nominal>1</Nominal>
            <Name>Доллар США</Name>
            <Value>87,1234</Value>     ← запятая как десятичный разделитель
          </Valute>
        </ValCurs>
    """
    try:
        root = etree.fromstring(raw.xml_content)
    except etree.XMLSyntaxError as exc:
        raise ProcessingError(f"Ошибка парсинга XML: {exc}") from exc

    try:
        rate_date = _parse_cbr_date(root.get("Date", ""))
    except ValueError:
        rate_date = date.today()

    result: dict[str, CurrencyRate] = {}
    for valute in root.findall("Valute"):
        try:
            char_code = _text(valute, "CharCode")
            nominal = int(_text(valute, "Nominal"))
            value = float(_text(valute, "Value").replace(",", ".")) / nominal
            result[char_code] = CurrencyRate(
                currency_id=char_code,
                name=_text(valute, "Name"),
                value=value,
                nominal=nominal,
                rate_date=rate_date,
            )
        except (ValueError, TypeError, AttributeError):
            continue

    if not result:
        raise ProcessingError("XML не содержит данных о курсах валют")
    return result


def parse_currency_history(raw: CbrRawData, currency_id: str) -> HistoryData:
    """
    Парсит XML с динамикой курса одной валюты.

    Формат XML-ответа ЦБ:
        <ValCurs name="Доллар США">
          <Record Date="01.01.2024">
            <Nominal>1</Nominal>
            <Value>88,1500</Value>
          </Record>
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
            nominal = int(_text(record, "Nominal"))
            value = float(_text(record, "Value").replace(",", ".")) / nominal
            dates.append(_parse_cbr_date(record.get("Date", "")))
            values.append(value)
        except (ValueError, TypeError, AttributeError):
            continue

    if not dates:
        raise ProcessingError(f"Нет данных о курсе {currency_id} за указанный период")

    paired = sorted(zip(dates, values), key=lambda x: x[0])
    dates, values = zip(*paired)  # type: ignore[assignment]

    return HistoryData(
        currency_id=currency_id,
        name=name,
        dates=list(dates),
        values=list(values),
        nominal=nominal,
    )


def _text(element: Any, tag: str) -> str:
    child = element.find(tag)
    if child is None or child.text is None:
        raise AttributeError(f"Тег <{tag}> не найден или пуст")
    return child.text.strip()


def _parse_cbr_date(date_str: str) -> date:
    """Парсит дату формата ЦБ РФ: 'DD.MM.YYYY'."""
    parts = date_str.split(".")
    if len(parts) != 3:
        raise ValueError(f"Неверный формат даты: {date_str!r}")
    return date(int(parts[2]), int(parts[1]), int(parts[0]))