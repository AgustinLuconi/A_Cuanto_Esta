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
    parser.add_argument("--all", action="store_true", help="Fetch all data")
    args = parser.parse_args()

    # Si no se especifica nada, por defecto obtener todo (comportamiento original)
    fetch_all = args.all or (not args.inflation and not args.dollars)

    client = ArgentinaDatosClient()
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

        if fetch_all or args.dollars:
            # Dólar blue
            records = client.get_dollar_blue()
            saved = processor.save_dollar_data(records, IndicatorType.DOLLAR_BLUE)
            print(f"[dollar_blue] Guardados: {saved} nuevos registros")

            # Dólar oficial
            records = client.get_dollar_oficial()
            saved = processor.save_dollar_data(records, IndicatorType.DOLLAR_OFICIAL)
            print(f"[dollar_oficial] Guardados: {saved} nuevos registros")

            # DolarAPI — cotizaciones actuales
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
