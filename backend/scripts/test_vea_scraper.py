"""
Script de prueba para VeaScraper.

Uso:
    cd backend
    source venv/bin/activate

    # Solo imprime en consola (sin tocar DB)
    python3 scripts/test_vea_scraper.py

    # Guarda en DB
    python3 scripts/test_vea_scraper.py --save
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.vea import VeaScraper

SEARCH_TERMS = ["leche", "aceite", "arroz"]
MAX_PER_TERM = 5  # solo para prueba rápida


def main():
    save_to_db = "--save" in sys.argv
    scraper = VeaScraper()

    if save_to_db:
        from app.config.database import SessionLocal
        session = SessionLocal()
        try:
            total_new = scraper.scrape(
                db_session=session,
                search_terms=SEARCH_TERMS,
                max_per_term=MAX_PER_TERM,
            )
            print(f"\n[vea] Total nuevos productos en DB: {total_new}")
        finally:
            session.close()
    else:
        print("[vea] Modo prueba — solo consola (usar --save para guardar en DB)\n")
        scraper.scrape(
            db_session=None,
            search_terms=SEARCH_TERMS,
            max_per_term=MAX_PER_TERM,
        )


if __name__ == "__main__":
    main()
