"""
Script standalone para sincronizar los datasets del INDEC en la tabla
indec_observations.

Uso:
    cd backend
    source venv/bin/activate
    python scripts/fetch_indec_data.py                       # incremental, todos
    python scripts/fetch_indec_data.py --dataset ipc_nacional
    python scripts/fetch_indec_data.py --full                # backfill completo

Código de salida distinto de 0 si falta el token, el INDEC falla o un dataset
trae 0 filas (así el job de GitHub Actions no queda "en verde" en falso).
"""
import argparse
import os
import sys

# Agregar backend/ al path para poder importar app.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.services.indec.client import IndecClient, IndecError
from app.services.indec.registry import get_specs
from app.services.indec.sync import sync_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sincronizar datos del INDEC")
    parser.add_argument("--dataset", help="slug de un dataset (por defecto, todos)")
    parser.add_argument("--full", action="store_true", help="backfill completo, sin ventana incremental")
    args = parser.parse_args(argv)

    try:
        specs = get_specs(args.dataset)
        client = IndecClient()  # falla acá si falta el token, antes de abrir la base
    except (ValueError, IndecError) as e:
        print(f"[indec] {e}")
        return 1

    session = SessionLocal()
    try:
        report = sync_all(session, client, specs, full=args.full)
    finally:
        session.close()

    for r in report.results:
        print(f"[{r.dataset}] pedidas: {r.fetched} | nuevas: {r.inserted} | actualizadas: {r.updated}")
    for slug, error in report.errors.items():
        print(f"[{slug}] ERROR: {error}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
