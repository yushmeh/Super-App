import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.currency_tracker.api.cbr_client import CbrRawData
from modules.currency_tracker.logic.data_processor import (
    parse_daily_rates, parse_currency_history, ProcessingError,
)


def _daily_xml(date_attr: str = "10.06.2024", valutes: str = "") -> bytes:
    return f'<ValCurs Date="{date_attr}" name="Foreign Currency Market">{valutes}</ValCurs>'.encode("utf-8")


def _valute_xml(char_code: str, name: str, nominal: int, value: str, vid: str = "R01235") -> str:
    return (
        f'<Valute ID="{vid}">'
        f'<NumCode>840</NumCode><CharCode>{char_code}</CharCode>'
        f'<Nominal>{nominal}</Nominal><Name>{name}</Name><Value>{value}</Value>'
        f'</Valute>'
    )


def _history_xml(name: str = "Доллар США", records: str = "") -> bytes:
    return f'<ValCurs ID="R01235" name="{name}">{records}</ValCurs>'.encode("utf-8")


def _record_xml(date_attr: str, nominal: int, value: str) -> str:
    return f'<Record Date="{date_attr}"><Nominal>{nominal}</Nominal><Value>{value}</Value></Record>'


class TestParseDailyRates:

    def test_parses_single_valute(self) -> None:
        xml = _daily_xml(valutes=_valute_xml("USD", "Доллар США", 1, "87,1234"))
        raw = CbrRawData(xml_content=xml, query_type="daily")
        result = parse_daily_rates(raw)
        assert "USD" in result
        assert result["USD"].value == pytest.approx(87.1234)

    def test_parses_multiple_valutes(self) -> None:
        xml = _daily_xml(valutes=(
            _valute_xml("USD", "Доллар США", 1, "87,1234") +
            _valute_xml("EUR", "Евро", 1, "94,5678", vid="R01239")
        ))
        raw = CbrRawData(xml_content=xml, query_type="daily")
        result = parse_daily_rates(raw)
        assert len(result) == 2
        assert "EUR" in result

    def test_normalizes_by_nominal(self) -> None:
        # JPY обычно имеет nominal=100
        xml = _daily_xml(valutes=_valute_xml("JPY", "Иена", 100, "55,5500"))
        raw = CbrRawData(xml_content=xml, query_type="daily")
        result = parse_daily_rates(raw)
        assert result["JPY"].value == pytest.approx(0.5555)

    def test_parses_rate_date(self) -> None:
        xml = _daily_xml(date_attr="15.03.2024", valutes=_valute_xml("USD", "Доллар США", 1, "90,0"))
        raw = CbrRawData(xml_content=xml, query_type="daily")
        result = parse_daily_rates(raw)
        assert result["USD"].rate_date.isoformat() == "2024-03-15"

    def test_empty_valutes_raises(self) -> None:
        xml = _daily_xml(valutes="")
        raw = CbrRawData(xml_content=xml, query_type="daily")
        with pytest.raises(ProcessingError, match="не содержит"):
            parse_daily_rates(raw)

    def test_invalid_xml_raises(self) -> None:
        raw = CbrRawData(xml_content=b"<not valid xml", query_type="daily")
        with pytest.raises(ProcessingError):
            parse_daily_rates(raw)

    def test_skips_malformed_valute(self) -> None:
        # Один валидный, один с некорректным значением
        bad_valute = (
            '<Valute ID="R01XXX"><CharCode>BAD</CharCode>'
            '<Nominal>1</Nominal><Name>Битая</Name><Value>not_a_number</Value></Valute>'
        )
        xml = _daily_xml(valutes=_valute_xml("USD", "Доллар США", 1, "87,0") + bad_valute)
        raw = CbrRawData(xml_content=xml, query_type="daily")
        result = parse_daily_rates(raw)
        assert "USD" in result
        assert "BAD" not in result


class TestParseCurrencyHistory:

    def test_parses_records(self) -> None:
        xml = _history_xml(records=(
            _record_xml("01.01.2024", 1, "88,0000") +
            _record_xml("02.01.2024", 1, "88,5000")
        ))
        raw = CbrRawData(xml_content=xml, query_type="dynamic")
        result = parse_currency_history(raw, "USD")
        assert len(result.dates) == 2
        assert result.values[0] == pytest.approx(88.0)

    def test_sorts_by_date(self) -> None:
        xml = _history_xml(records=(
            _record_xml("05.01.2024", 1, "89,0000") +
            _record_xml("01.01.2024", 1, "88,0000")
        ))
        raw = CbrRawData(xml_content=xml, query_type="dynamic")
        result = parse_currency_history(raw, "USD")
        assert result.dates[0].isoformat() == "2024-01-01"
        assert result.dates[1].isoformat() == "2024-01-05"

    def test_normalizes_by_nominal(self) -> None:
        xml = _history_xml(records=_record_xml("01.01.2024", 100, "55,0000"))
        raw = CbrRawData(xml_content=xml, query_type="dynamic")
        result = parse_currency_history(raw, "JPY")
        assert result.values[0] == pytest.approx(0.55)

    def test_empty_records_raises(self) -> None:
        xml = _history_xml(records="")
        raw = CbrRawData(xml_content=xml, query_type="dynamic")
        with pytest.raises(ProcessingError, match="Нет данных"):
            parse_currency_history(raw, "USD")

    def test_invalid_xml_raises(self) -> None:
        raw = CbrRawData(xml_content=b"<broken", query_type="dynamic")
        with pytest.raises(ProcessingError):
            parse_currency_history(raw, "USD")

    def test_uses_currency_id_as_fallback_name(self) -> None:
        xml = f'<ValCurs ID="R01235">{_record_xml("01.01.2024", 1, "88,0")}</ValCurs>'.encode("utf-8")
        raw = CbrRawData(xml_content=xml, query_type="dynamic")
        result = parse_currency_history(raw, "USD")
        assert result.name == "USD"