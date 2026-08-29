"""
Pruebas unitarias para EconomicDataProcessor: lógica "skip if exists" y
deduplicación al persistir indicadores económicos. Se mockea la sesión de
SQLAlchemy — no se toca la base de datos real.
"""
import os
import sys
from datetime import date, datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.economic_indicator import IndicatorType
from app.services.economic_data.processor import EconomicDataProcessor
from app.services.economic_data.schemas import (
    InflationRecord,
    DollarRecord,
    UVARecord,
    DolarAPIQuote,
)


def _mock_session_with_exists_sequence(existing_sequence):
    """
    Mockea session.query(...).filter(...).first() para devolver, en orden,
    los valores de existing_sequence (None = no existe, algo = ya existe).
    """
    session = MagicMock()
    session.query.return_value.filter.return_value.first.side_effect = existing_sequence
    return session


def test_save_inflation_data_skips_existing_record_and_saves_new_one():
    # Arrange: primer registro ya existe en DB, segundo es nuevo
    records = [
        InflationRecord(fecha=date(2026, 1, 1), valor=4.2),
        InflationRecord(fecha=date(2026, 2, 1), valor=3.8),
    ]
    session = _mock_session_with_exists_sequence([object(), None])
    processor = EconomicDataProcessor(session)

    # Act
    saved = processor.save_inflation_data(records, IndicatorType.INFLATION_MONTHLY)

    # Assert
    assert saved == 1
    assert session.add.call_count == 1
    added_indicator = session.add.call_args[0][0]
    assert added_indicator.date == date(2026, 2, 1)
    assert float(added_indicator.value) == 3.8


def test_save_inflation_data_commits_once_regardless_of_record_count():
    # Arrange: ningún registro existe -> se agregan los 3
    records = [
        InflationRecord(fecha=date(2026, 1, 1), valor=1.0),
        InflationRecord(fecha=date(2026, 2, 1), valor=2.0),
        InflationRecord(fecha=date(2026, 3, 1), valor=3.0),
    ]
    session = _mock_session_with_exists_sequence([None, None, None])
    processor = EconomicDataProcessor(session)

    # Act
    saved = processor.save_inflation_data(records, IndicatorType.INFLATION_MONTHLY)

    # Assert
    assert saved == 3
    assert session.add.call_count == 3
    session.commit.assert_called_once()


def test_save_all_dollars_ignores_casa_without_mapped_indicator_type():
    # Arrange: "solidario" no tiene IndicatorType mapeado -> debe ignorarse
    # completamente (ni siquiera debe consultar fechas existentes para esa casa).
    records = [
        DollarRecord(casa="solidario", venta=1000.0, compra=990.0, fecha=date(2026, 1, 1)),
    ]
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = []
    processor = EconomicDataProcessor(session)

    # Act
    result = processor.save_all_dollars(records)

    # Assert
    assert result == {}
    session.add.assert_not_called()
    session.commit.assert_called_once()


def test_save_all_dollars_skips_records_already_in_db():
    # Arrange: la fecha 2026-01-01 ya existe en DB para "blue"
    records = [
        DollarRecord(casa="blue", venta=1300.0, compra=1280.0, fecha=date(2026, 1, 1)),
        DollarRecord(casa="blue", venta=1310.0, compra=1290.0, fecha=date(2026, 1, 2)),
    ]
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [(date(2026, 1, 1),)]
    processor = EconomicDataProcessor(session)

    # Act
    result = processor.save_all_dollars(records)

    # Assert: solo se guarda el registro del 1/2, el del 1/1 se saltea
    assert result == {"blue": 1}
    assert session.add.call_count == 1
    added = session.add.call_args[0][0]
    assert added.date == date(2026, 1, 2)


def test_save_all_dollars_skips_duplicate_dates_within_same_batch():
    # Arrange: dos registros de "oficial" con la MISMA fecha en el mismo batch.
    # Ninguno existe todavía en DB, pero solo el primero debe guardarse:
    # el set `existing` se actualiza en memoria durante el loop.
    records = [
        DollarRecord(casa="oficial", venta=1000.0, compra=990.0, fecha=date(2026, 1, 5)),
        DollarRecord(casa="oficial", venta=1001.0, compra=991.0, fecha=date(2026, 1, 5)),
    ]
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = []
    processor = EconomicDataProcessor(session)

    # Act
    result = processor.save_all_dollars(records)

    # Assert
    assert result == {"oficial": 1}
    assert session.add.call_count == 1


def test_save_dolar_api_quotes_ignores_unmapped_casa_and_uses_date_only():
    # Arrange: "mayorista" no está en _CASA_TO_INDICATOR (solo blue/oficial/bolsa/ccl)
    quotes = [
        DolarAPIQuote(
            moneda="USD",
            casa="mayorista",
            nombre="Mayorista",
            compra=1000.0,
            venta=1005.0,
            fechaActualizacion=datetime(2026, 1, 1, 15, 30),
        ),
        DolarAPIQuote(
            moneda="USD",
            casa="blue",
            nombre="Blue",
            compra=1300.0,
            venta=1320.0,
            fechaActualizacion=datetime(2026, 1, 1, 15, 30),
        ),
    ]
    session = _mock_session_with_exists_sequence([None])
    processor = EconomicDataProcessor(session)

    # Act
    saved = processor.save_dolar_api_quotes(quotes)

    # Assert: solo "blue" se guarda; se usa solo la parte de fecha (sin hora)
    assert saved == 1
    assert session.add.call_count == 1
    added = session.add.call_args[0][0]
    assert added.date == date(2026, 1, 1)


def test_save_uva_data_skips_existing_and_saves_new():
    records = [
        UVARecord(fecha=date(2026, 1, 1), valor=1500.0),
        UVARecord(fecha=date(2026, 1, 2), valor=1501.5),
    ]
    session = _mock_session_with_exists_sequence([object(), None])
    processor = EconomicDataProcessor(session)

    saved = processor.save_uva_data(records)

    assert saved == 1
    added = session.add.call_args[0][0]
    assert added.date == date(2026, 1, 2)
