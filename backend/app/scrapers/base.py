"""
Clase base abstracta para todos los scrapers del proyecto.
Define la interfaz común y manejo de HTTP/delays.
"""
import re
import time
from abc import ABC, abstractmethod

import requests

from app.config.settings import settings
from app.models.product import Product
from app.models.product_alias import ProductAlias, MatchType
from app.services.product_matcher import find_matching_product

_BARCODE_RE = re.compile(r"^\d{8,14}$")


def is_real_barcode(barcode: str | None) -> bool:
    """True si el barcode es un EAN/UPC real (8-14 dígitos numéricos)."""
    return bool(barcode and _BARCODE_RE.match(barcode))


class BaseScraper(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.USER_AGENT})
        self.delay = settings.SCRAPING_DELAY
        self.timeout = settings.SCRAPING_TIMEOUT
        self.max_retries = 3
        self.retry_base_delay = 5
        self.default_province = None
        self.default_region = None
        self.default_city = None

    def _get(self, url: str, params: dict = None) -> dict | None:
        """GET con retry automático para HTTP 429 y delay post-request."""
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                time.sleep(self.delay)
                return response.json()
            except requests.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    wait = self.retry_base_delay * (2 ** attempt)
                    print(f"[scraper] HTTP 429 en {url} — reintento {attempt + 1}/{self.max_retries} en {wait}s")
                    time.sleep(wait)
                    continue
                print(f"[scraper] HTTP {e.response.status_code} en {url}")
                time.sleep(self.delay)
                return None
            except requests.RequestException as e:
                print(f"[scraper] Error de red en {url}: {e}")
                time.sleep(self.delay)
                return None
        return None

    @abstractmethod
    def scrape(self, **kwargs) -> int:
        """Ejecuta el scraping completo. Retorna cantidad de nuevos productos."""
        ...

    @abstractmethod
    def parse_product(self, raw: dict) -> dict | None:
        """Convierte un item crudo de la API/HTML en un dict normalizado para DB."""
        ...

    def _create_product(self, db_session, product_data: dict, barcode: str | None) -> Product:
        """Crea y hace flush de un nuevo Product. No hace commit."""
        p = Product(
            name=product_data["name"],
            normalized_name=product_data["normalized_name"],
            brand=product_data.get("brand"),
            category=product_data["category"],
            unit=product_data["unit"],
            quantity=product_data.get("quantity"),
            image_url=product_data.get("image_url"),
            barcode=barcode,
        )
        db_session.add(p)
        db_session.flush()
        return p

    def _get_or_create_product(
        self,
        db_session,
        barcode: str | None,
        store_name: str,
        product_data: dict,
    ) -> tuple[Product, bool]:
        """
        Estrategia de deduplicación para scrapers sin EAN real.

        Barcode real (8-14 dígitos) → buscar por barcode, crear si no existe.
        Barcode interno (ej: 'la_anonima_123'):
          1. Buscar en product_aliases → usar canónico si existe.
          2. Fuzzy matching ≥85% → crear alias FUZZY, retornar canónico.
          3. Sin match → crear Product nuevo + alias de identidad (confidence=1.0).

        Returns:
            (product, is_new) donde is_new=True solo si se creó un Product nuevo.
        """
        if is_real_barcode(barcode):
            p = db_session.query(Product).filter_by(barcode=barcode).first()
            if p:
                if p.image_url is None and product_data.get("image_url"):
                    p.image_url = product_data["image_url"]
                return p, False
            return self._create_product(db_session, product_data, barcode), True

        # Barcode interno: buscar alias existente primero
        existing_alias = (
            db_session.query(ProductAlias)
            .filter_by(alias_source=store_name, alias_id=barcode)
            .first()
        )
        if existing_alias:
            p = db_session.get(Product, existing_alias.canonical_product_id)
            if p:
                if p.image_url is None and product_data.get("image_url"):
                    p.image_url = product_data["image_url"]
                return p, False

        # Fuzzy matching contra productos existentes
        match, confidence = find_matching_product(
            name=product_data["name"],
            brand=product_data.get("brand"),
            quantity=product_data.get("quantity"),
            unit=product_data.get("unit"),
            db=db_session,
        )

        if match and confidence >= 0.85:
            db_session.add(ProductAlias(
                alias_source=store_name,
                alias_id=barcode,
                canonical_product_id=match.id,
                match_type=MatchType.FUZZY,
                confidence=confidence,
            ))
            return match, False

        # Sin match: producto nuevo + alias de identidad
        new_p = self._create_product(db_session, product_data, barcode)
        db_session.add(ProductAlias(
            alias_source=store_name,
            alias_id=barcode,
            canonical_product_id=new_p.id,
            match_type=MatchType.FUZZY,
            confidence=1.0,
        ))
        return new_p, True
