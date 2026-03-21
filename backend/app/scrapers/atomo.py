"""
Scraper de Átomo (atomoconviene.com) via endpoint AJAX de PrestaShop.

Átomo es un supermercado de Mendoza que usa PrestaShop.
Expone un endpoint de búsqueda AJAX que devuelve JSON estructurado con
precios numéricos, descuentos e imágenes. No requiere headless browser.
"""
import re

from app.models.product import Product, ProductCategory, ProductUnit
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.base import BaseScraper
from app.scrapers.utils.normalizer import (
    normalize_product_name,
    map_category,
    map_unit,
)

BASE_URL = "https://atomoconviene.com/atomo-ecommerce"
SEARCH_URL = f"{BASE_URL}/index.php"
PER_PAGE = 100


class AtomoScraper(BaseScraper):
    """
    Scraper de Átomo.
    Usa el endpoint AJAX de búsqueda de PrestaShop para obtener productos en JSON.
    """

    def __init__(self):
        super().__init__()
        self.session.headers.update({"X-Requested-With": "XMLHttpRequest"})

    def search(self, query: str, page: int = 1) -> dict | None:
        """Llama al endpoint AJAX de búsqueda de PrestaShop."""
        return self._get(SEARCH_URL, params={
            "controller": "search",
            "s": query,
            "resultsPerPage": PER_PAGE,
            "ajax": "true",
            "page": page,
        })

    def parse_product(self, raw: dict) -> dict | None:
        """
        Convierte un item crudo del AJAX de Átomo en un dict normalizado para DB.
        Retorna None si faltan campos críticos.
        """
        name = raw.get("name")
        price = raw.get("price_amount")
        if not name or price is None:
            return None

        url = raw.get("url", "")
        original_price = raw.get("regular_price_amount")
        on_sale = original_price is not None and float(original_price) > float(price)

        discount_pct = None
        if on_sale and original_price:
            discount_pct = round((1 - float(price) / float(original_price)) * 100, 2)

        # Barcode desde la URL: "--12345678901234.html"
        barcode = None
        barcode_match = re.search(r"--(\d{8,13})\.html$", url)
        if barcode_match:
            barcode = barcode_match.group(1)

        # Categoría inferida desde los segmentos del path de la URL
        category = _category_from_url(url)

        # Imagen
        cover = raw.get("cover") or {}
        medium = cover.get("medium") or {}
        image_url = medium.get("url")

        return {
            "name": name,
            "normalized_name": normalize_product_name(name),
            "brand": None,  # Átomo no expone marca en este endpoint
            "category": category,
            "unit": map_unit("", ""),  # Sin info de unidad en el JSON — default UNIDAD
            "quantity": None,
            "image_url": image_url,
            "barcode": barcode,
            "price": float(price),
            "original_price": float(original_price) if on_sale else None,
            "was_on_sale": on_sale,
            "discount_percentage": discount_pct,
            "url": url or None,
            "in_stock": raw.get("active") == "1",
        }

    def _save_product(self, db_session, product_data: dict) -> bool:
        """
        Busca Product por barcode (crea si no existe) y registra PriceHistory.
        Retorna True si el producto es nuevo.
        """
        barcode = product_data.get("barcode")
        product = None
        if barcode:
            product = db_session.query(Product).filter(Product.barcode == barcode).first()

        is_new = product is None
        if is_new:
            product = Product(
                name=product_data["name"],
                normalized_name=product_data["normalized_name"],
                brand=product_data.get("brand"),
                category=product_data["category"],
                unit=product_data["unit"],
                quantity=product_data.get("quantity"),
                image_url=product_data.get("image_url"),
                barcode=barcode,
            )
            db_session.add(product)
            db_session.flush()  # Genera UUID antes de crear PriceHistory

        db_session.add(PriceHistory(
            product_id=product.id,
            supermarket=Supermarket.ATOMO,
            price=product_data["price"],
            was_on_sale=product_data["was_on_sale"],
            original_price=product_data.get("original_price"),
            discount_percentage=product_data.get("discount_percentage"),
            url=product_data.get("url"),
            in_stock=product_data["in_stock"],
        ))
        return is_new

    def scrape(self, db_session=None, search_terms: list[str] = None, max_per_term: int = 200) -> int:
        """
        Ejecuta el scraping completo.
        - db_session=None → solo imprime en consola (modo prueba)
        - db_session=<session> → guarda en DB
        Retorna cantidad de nuevos productos creados.
        """
        if search_terms is None:
            search_terms = ["leche", "aceite", "arroz", "fideos", "yerba"]

        total_new = 0

        for term in search_terms:
            page = 1
            term_count = 0

            while True:
                if term_count >= max_per_term:
                    break

                print(f"[atomo] Buscando: '{term}' (pág. {page})...")
                data = self.search(term, page=page)
                if not data:
                    break

                products_raw = data.get("products") or []
                pages_count = data.get("pagination", {}).get("pages_count", 1)

                if not products_raw:
                    break

                batch_new = 0
                for raw in products_raw:
                    if term_count >= max_per_term:
                        break

                    product_data = self.parse_product(raw)
                    if not product_data:
                        continue

                    term_count += 1
                    if db_session:
                        if self._save_product(db_session, product_data):
                            batch_new += 1
                    else:
                        _print_product(product_data)

                if db_session:
                    db_session.commit()
                    total_new += batch_new

                if page >= pages_count:
                    break
                page += 1

            print(f"[atomo] '{term}': {term_count} productos procesados")

        return total_new


def _category_from_url(url: str) -> ProductCategory:
    """
    Infiere ProductCategory desde los segmentos del path de la URL de Átomo.
    Ej: .../leches/leche-modif--8445.html → LACTEOS
    """
    path_segments = [seg.lower() for seg in url.split("/") if seg]
    fake_groups = [
        {"display_name": seg, "path_list": [{"display_name": seg}]}
        for seg in path_segments
    ]
    return map_category(fake_groups)


def _print_product(p: dict) -> None:
    """Imprime un producto en consola (modo prueba sin DB)."""
    price_str = f"${p['price']:,.2f}"
    if p["was_on_sale"] and p["original_price"]:
        price_str += f" (antes ${p['original_price']:,.2f}, -{p['discount_percentage']:.0f}%)"
    print(
        f"  ✓ {p['name'][:60]:<60} | {price_str} | "
        f"Barcode: {p.get('barcode') or '—'} | Cat: {p['category'].name}"
    )
