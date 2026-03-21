"""
Scraper de Carrefour Argentina via API pública de VTEX.

Carrefour Argentina usa VTEX como plataforma e-commerce.
Expone un endpoint de búsqueda REST que devuelve JSON estructurado con
precios numéricos, EAN, marca e imágenes. No requiere autenticación ni
headless browser.

CarrefourScraper también es la clase base para otros supermercados VTEX
(Vea, Disco): subclasear y sobreescribir solo __init__.
"""
import urllib.parse

from app.config.settings import settings
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.base import BaseScraper
from app.scrapers.utils.normalizer import (
    normalize_product_name,
    map_category,
    map_unit,
)

PER_PAGE = 50
_VTEX_SEARCH_PATH = "/api/catalog_system/pub/products/search"


class CarrefourScraper(BaseScraper):
    """
    Scraper de Carrefour Argentina (VTEX).
    La respuesta es un array JSON raíz (no un objeto con clave 'results').

    Subclaseable para otros supermercados VTEX: sobreescribir solo __init__
    para cambiar name, search_url, store_url y supermarket_enum.
    """

    def __init__(self):
        super().__init__()
        self.name             = "carrefour"
        self.search_url       = f"{settings.CARREFOUR_API_URL}{_VTEX_SEARCH_PATH}"
        self.store_url        = settings.CARREFOUR_STORE_URL
        self.supermarket_enum = Supermarket.CARREFOUR

    def search(self, query: str, from_: int = 0) -> list | None:
        """Llama al endpoint de búsqueda de VTEX."""
        result = self._get(self.search_url, params={
            "ft": urllib.parse.quote(query),
            "_from": from_,
            "_to": from_ + PER_PAGE - 1,
        })
        # VTEX devuelve un array JSON raíz; _get() lo deserializa a list.
        return result if isinstance(result, list) else None

    def parse_product(self, raw: dict) -> dict | None:
        """
        Convierte un item crudo de la API VTEX en un dict normalizado para DB.
        Retorna None si faltan campos críticos.
        """
        name = raw.get("productName")
        items = raw.get("items") or []
        if not name or not items:
            return None

        item = items[0]
        sellers = item.get("sellers") or []
        offer = sellers[0].get("commertialOffer", {}) if sellers else {}

        price = offer.get("Price")
        if price is None:
            return None

        list_price = offer.get("ListPrice")
        on_sale = list_price is not None and float(list_price) > float(price)

        discount_pct = None
        if on_sale and list_price:
            discount_pct = round((1 - float(price) / float(list_price)) * 100, 2)

        # Guard: ignorar descuentos irreales (errores de catálogo VTEX)
        if on_sale and discount_pct is not None and discount_pct > 80:
            on_sale, discount_pct, list_price = False, None, None

        barcode = item.get("ean") or None
        image_url = ((item.get("images") or [{}])[0]).get("imageUrl")
        url = f"{self.store_url}/{raw['linkText']}/p"
        category = _category_from_vtex(raw.get("categories") or [])
        in_stock = int(offer.get("AvailableQuantity") or 0) > 0

        return {
            "name": name,
            "normalized_name": normalize_product_name(name),
            "brand": raw.get("brand"),
            "category": category,
            "unit": map_unit("", ""),  # VTEX no expone unidad en este endpoint
            "quantity": None,
            "image_url": image_url,
            "barcode": barcode,
            "price": float(price),
            "original_price": float(list_price) if on_sale else None,
            "was_on_sale": on_sale,
            "discount_percentage": discount_pct,
            "url": url,
            "in_stock": in_stock,
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
            supermarket=self.supermarket_enum,
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
            from_ = 0
            term_count = 0

            while True:
                if term_count >= max_per_term:
                    break

                print(f"[{self.name}] Buscando: '{term}' (desde {from_})...")
                results = self.search(term, from_=from_)
                if not results:
                    break

                batch_new = 0
                for raw in results:
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

                # Fin de resultados cuando la página está incompleta
                if len(results) < PER_PAGE:
                    break
                from_ += PER_PAGE

            print(f"[{self.name}] '{term}': {term_count} productos procesados")

        return total_new


def _category_from_vtex(categories: list[str]) -> ProductCategory:
    """
    Infiere ProductCategory desde el path de categoría VTEX.
    Ej: ["/Almacén/Fideos/", "/Almacén/"] → ALIMENTOS
    """
    for cat_path in categories:
        segments = [seg.lower() for seg in cat_path.split("/") if seg]
        fake_groups = [
            {"display_name": seg, "path_list": [{"display_name": seg}]}
            for seg in segments
        ]
        result = map_category(fake_groups)
        if result.name != "OTROS":
            return result
    return map_category([])  # → OTROS


def _print_product(p: dict) -> None:
    """Imprime un producto en consola (modo prueba sin DB)."""
    price_str = f"${p['price']:,.2f}"
    if p["was_on_sale"] and p["original_price"]:
        price_str += f" (antes ${p['original_price']:,.2f}, -{p['discount_percentage']:.0f}%)"
    print(
        f"  ✓ {p['name'][:55]:<55} | {price_str} | "
        f"Marca: {p.get('brand') or '—'} | Cat: {p['category'].name}"
    )
