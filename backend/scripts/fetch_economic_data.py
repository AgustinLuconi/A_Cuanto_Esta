"""
Script standalone para poblar economic_indicators desde la API ArgentinaDatos.

Uso:
    cd backend
    source venv/bin/activate
    python scripts/fetch_economic_data.py
"""
import sys
import os

# Agregar backend/ al path para poder importar app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.economic_indicator import IndicatorType
from app.services.economic_data.client import ArgentinaDatosClient, DolarAPIClient
from app.services.economic_data.processor import EconomicDataProcessor


import argparse

def main():
    parser = argparse.ArgumentParser(description="Fetch economic data")
    parser.add_argument("--inflation", action="store_true", help="Fetch inflation data")
    parser.add_argument("--dollars", action="store_true", help="Fetch dollar data")
    parser.add_argument("--risk-country", action="store_true", help="Fetch country risk data")
    parser.add_argument("--all", action="store_true", help="Fetch all data")
    args = parser.parse_args()

    # Si no se especifica nada, por defecto obtener todo (comportamiento original)
    fetch_all = args.all or (not args.inflation and not args.dollars and not args.risk_country)

    client = ArgentinaDatosClient()

    # Chequeo defensivo: si ArgentinaDatos está caído, cortar acá con exit code
    # distinto de 0 en vez de seguir y terminar "en verde" con 0 registros
    # nuevos guardados (eso es indistinguible de un día sin novedades).
    estado = client.get_estado()
    if estado != "Correcto":
        print(f"[estado] ArgentinaDatos no responde correctamente (estado={estado!r}). Abortando.")
        sys.exit(1)
    print(f"[estado] ArgentinaDatos OK (estado={estado!r})")

    session = SessionLocal()

    try:
        processor = EconomicDataProcessor(session)

        if fetch_all or args.inflation:
            # Inflación mensual
            records = client.get_inflation()
            saved = processor.save_inflation_data(records, IndicatorType.INFLATION_MONTHLY)
            print(f"[inflacion] Guardados: {saved} nuevos registros")

            # UVA
            records = client.get_uva()
            saved = processor.save_uva_data(records)
            print(f"[uva] Guardados: {saved} nuevos registros")

            # Inflación interanual
            records = client.get_inflation_yearly()
            if records:
                saved = processor.save_inflation_data(records, IndicatorType.INFLATION_YEARLY)
                print(f"[inflacion_interanual] Guardados: {saved} nuevos registros")
            else:
                print("[inflacion_interanual] Endpoint no disponible, saltando.")

        if fetch_all or args.risk_country:
            records = client.get_risk_country()
            saved = processor.save_inflation_data(records, IndicatorType.RISK_COUNTRY)
            print(f"[riesgo_pais] Guardados: {saved} nuevos registros")

        if fetch_all or args.dollars:
            # Todas las casas de cambio — histórico combinado, ArgentinaDatos
            all_dollars = client.get_all_dollars()
            saved_per_casa = processor.save_all_dollars(all_dollars)
            for casa, count in saved_per_casa.items():
                print(f"[dolar_{casa}] Guardados: {count} nuevos registros")

            # DolarAPI — fallback de cotización del día para blue/oficial/MEP/CCL
            dolar_client = DolarAPIClient()
            quotes = dolar_client.get_all_quotes()
            saved = processor.save_dolar_api_quotes(quotes)
            print(f"[dolarapi] Guardados: {saved} nuevos registros")
            for q in quotes:
                print(f"  {q.nombre}: compra={q.compra} venta={q.venta}")

    finally:
        session.close()

if __name__ == "__main__":
    main()
