"""
modules/currency_tracker/api/cbr_client.py
==========================================
Слой данных: async HTTP-клиент для XML API Центрального Банка РФ.

Эндпоинты ЦБ:
  Курс на дату:   https://www.cbr.ru/scripts/XML_daily.asp?date_req=DD/MM/YYYY
  История курса:  https://www.cbr.ru/scripts/XML_dynamic.asp?...&VAL_NM_RQ=R-код

Отвечает только за получение сырых данных.
Парсинг и валидация — в слое logic (data_processor.py).
"""
from __future__ import annotations

from datetime import date
from typing import NamedTuple

import httpx

_CBR_BASE   = "https://www.cbr.ru/scripts"
_URL_DAILY  = f"{_CBR_BASE}/XML_daily.asp"
_URL_DYNAMIC = f"{_CBR_BASE}/XML_dynamic.asp"
_TIMEOUT    = 10.0

CURRENCY_CODES: dict[str, str] = {
    "USD": "R01235",
    "EUR": "R01239",
    "CNY": "R01375",
    "GBP": "R01035",
    "JPY": "R01820",
    "CHF": "R01775",
    "HKD": "R01200",
    "TRY": "R01700J",
}


class CbrRawData(NamedTuple):
    """Контейнер для сырого XML-ответа ЦБ."""
    xml_content: bytes
    query_type: str  # "daily" | "dynamic"


class CbrApiError(Exception):
    """Ошибка при запросе к API ЦБ."""


async def fetch_daily_rates(query_date: date | None = None) -> CbrRawData:
    """
    Курсы всех валют на указанную дату.
    Если query_date не передан — возвращает актуальный курс.
    """
    params: dict[str, str] = {}
    if query_date is not None:
        params["date_req"] = query_date.strftime("%d/%m/%Y")
    return await _get(_URL_DAILY, params, "daily")


async def fetch_currency_history(
    currency_id: str,
    date_from: date,
    date_to: date,
) -> CbrRawData:
    """
    История курса одной валюты за диапазон дат.
    Выбрасывает ValueError если currency_id не найден в CURRENCY_CODES.
    """
    if currency_id not in CURRENCY_CODES:
        raise ValueError(
            f"Неизвестный код валюты: {currency_id!r}. "
            f"Доступные: {list(CURRENCY_CODES.keys())}"
        )
    params = {
        "date_req1": date_from.strftime("%d/%m/%Y"),
        "date_req2": date_to.strftime("%d/%m/%Y"),
        "VAL_NM_RQ": CURRENCY_CODES[currency_id],
    }
    return await _get(_URL_DYNAMIC, params, "dynamic")


async def _get(url: str, params: dict[str, str], query_type: str) -> CbrRawData:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return CbrRawData(xml_content=response.content, query_type=query_type)
    except httpx.TimeoutException as exc:
        raise CbrApiError(f"Тайм-аут при запросе к ЦБ РФ: {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise CbrApiError(f"HTTP ошибка {exc.response.status_code} от ЦБ РФ") from exc
    except httpx.RequestError as exc:
        raise CbrApiError(f"Ошибка сети: {exc}") from exc