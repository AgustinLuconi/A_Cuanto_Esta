"""
Procesador que persiste registros de ArgentinaDatos en la tabla economic_indicators.
Implementa lógica "skip if exists" para evitar duplicados en (indicator_type, date).
"""
import json
from sqlalchemy.orm import Session

from app.models.economic_indicator import EconomicIndicator, IndicatorType, DataSource
from app.services.economic_data.schemas import InflationRecord, DollarRecord, UVARecord, DolarAPIQuote


class EconomicDataProcessor:
    def __init__(self, session: Session):
        self.session = session

    def _exists(self, indicator_type: IndicatorType, date) -> bool:
        return (
            self.session.query(EconomicIndicator)
            .filter(
                EconomicIndicator.indicator_type == indicator_type,
                EconomicIndicator.date == date,
            )
            .first()
            is not None
        )

    def save_inflation_data(
        self, records: list[InflationRecord], indicator_type: IndicatorType
    ) -> int:
        saved = 0
        for record in records:
            if self._exists(indicator_type, record.fecha):
                continue
            self.session.add(
                EconomicIndicator(
                    indicator_type=indicator_type,
                    value=record.valor,
                    date=record.fecha,
                    source=DataSource.ARGENTINADATOS,
                )
            )
            saved += 1
        self.session.commit()
        return saved

    def save_dollar_data(
        self, records: list[DollarRecord], indicator_type: IndicatorType
    ) -> int:
        saved = 0
        for record in records:
            if self._exists(indicator_type, record.fecha):
                continue
            self.session.add(
                EconomicIndicator(
                    indicator_type=indicator_type,
                    value=record.venta,
                    date=record.fecha,
                    source=DataSource.ARGENTINADATOS,
                    metadata_json=json.dumps({"compra": record.compra}),
                )
            )
            saved += 1
        self.session.commit()
        return saved

    _CASA_TO_INDICATOR = {
        "blue": IndicatorType.DOLLAR_BLUE,
        "oficial": IndicatorType.DOLLAR_OFICIAL,
        "bolsa": IndicatorType.DOLLAR_MEP,
        "contadoconliqui": IndicatorType.DOLLAR_CCL,
    }

    def save_dolar_api_quotes(self, quotes: list[DolarAPIQuote]) -> int:
        saved = 0
        for quote in quotes:
            indicator_type = self._CASA_TO_INDICATOR.get(quote.casa)
            if indicator_type is None:
                continue  # mayorista, cripto, tarjeta — sin IndicatorType mapeado
            date = quote.fechaActualizacion.date()
            if self._exists(indicator_type, date):
                continue
            self.session.add(
                EconomicIndicator(
                    indicator_type=indicator_type,
                    value=quote.venta,
                    date=date,
                    source=DataSource.DOLARAPI,
                    metadata_json=json.dumps({"compra": quote.compra, "nombre": quote.nombre}),
                )
            )
            saved += 1
        self.session.commit()
        return saved

    def save_uva_data(self, records: list[UVARecord]) -> int:
        saved = 0
        for record in records:
            if self._exists(IndicatorType.UVA_INDEX, record.fecha):
                continue
            self.session.add(
                EconomicIndicator(
                    indicator_type=IndicatorType.UVA_INDEX,
                    value=record.valor,
                    date=record.fecha,
                    source=DataSource.ARGENTINADATOS,
                )
            )
            saved += 1
        self.session.commit()
        return saved
