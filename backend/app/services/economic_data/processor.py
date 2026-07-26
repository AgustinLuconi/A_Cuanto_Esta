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

    def _existing_dates(self, indicator_type: IndicatorType) -> set:
        """
        Todas las fechas ya guardadas para un tipo de indicador, en una sola
        consulta. Reemplaza el patrón _exists()-por-fila para cargas masivas
        (el endpoint combinado de dólares trae ~30.000 registros de una vez).
        """
        rows = (
            self.session.query(EconomicIndicator.date)
            .filter(EconomicIndicator.indicator_type == indicator_type)
            .all()
        )
        return {row[0] for row in rows}

    _CASA_TO_DOLLAR_TYPE = {
        "blue": IndicatorType.DOLLAR_BLUE,
        "oficial": IndicatorType.DOLLAR_OFICIAL,
        "mayorista": IndicatorType.DOLLAR_MAYORISTA,
        "bolsa": IndicatorType.DOLLAR_MEP,
        "contadoconliqui": IndicatorType.DOLLAR_CCL,
        "cripto": IndicatorType.DOLLAR_CRIPTO,
        "tarjeta": IndicatorType.DOLLAR_TARJETA,
    }

    def save_all_dollars(self, records: list[DollarRecord]) -> dict:
        """
        Guarda el histórico combinado de /v1/cotizaciones/dolares (todas las
        casas). Agrupa por casa y hace un solo SELECT de fechas existentes
        por tipo de indicador (no por fila) antes de insertar.
        Devuelve {casa: cantidad_guardada} para logging. Casas sin
        IndicatorType mapeado (ej. "solidario") se ignoran.
        """
        by_casa: dict[str, list[DollarRecord]] = {}
        for record in records:
            by_casa.setdefault(record.casa, []).append(record)

        saved_per_casa: dict[str, int] = {}
        for casa, casa_records in by_casa.items():
            indicator_type = self._CASA_TO_DOLLAR_TYPE.get(casa)
            if indicator_type is None:
                continue
            existing = self._existing_dates(indicator_type)
            saved = 0
            for record in casa_records:
                if record.fecha in existing:
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
                existing.add(record.fecha)
                saved += 1
            saved_per_casa[casa] = saved

        self.session.commit()
        return saved_per_casa

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
