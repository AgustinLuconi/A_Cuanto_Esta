"""
Scraper de Coto Digital via API de Constructor.io.

Coto usa Constructor.io (cnstrc.com) como motor de búsqueda/catálogo.
La API key pública está embebida en el JavaScript del sitio.
No se necesita headless browser — todo es JSON estructurado.
"""
from app.config.settings import settings
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.base import BaseScraper
from app.scrapers.utils.normalizer import (
    normalize_product_name,
    map_category,
    map_unit,
    parse_discount_price,
    build_quantity_str,
)

COTO_PRODUCT_URL_PREFIX = f"{settings.COTO_BASE_URL}/sitios/cdigi/p"


class CotoScraper(BaseScraper):
    """
    Scraper de Coto Digital.
    Usa el endpoint de búsqueda de Constructor.io para obtener productos en JSON.
    """

    PER_PAGE = 100

    def search(self, query: str, page: int = 1, per_page: int = None) -> dict | None:
        """Llama al endpoint de búsqueda de Constructor.io."""
        url = f"{settings.CONSTRUCTOR_API_URL}/search/{query}"
        return self._get(url, params={
            "key": settings.COTO_CONSTRUCTOR_KEY,
            "num_results_per_page": per_page or self.PER_PAGE,
            "page": page,
        })

    def parse_product(self, result: dict) -> dict | None:
        """
        Convierte un resultado de Constructor.io en un dict normalizado para DB.
        Retorna None si faltan campos críticos.
        """
        data = result.get("data", {})

        name = data.get("sku_display_name") or result.get("value")
        list_price = data.get("product_list_price")
        if not name or not list_price:
            return None

        # Descuentos y oferta
        discounts = data.get("discounts") or []
        sale_types = data.get("sale_type") or []
        on_sale = bool(discounts) and bool(sale_types)

        discounted_price = None
        discount_pct = None
        if on_sale:
            discounted_price = parse_discount_price(
                discounts[0].get("discountPrice", "")
            )
            if discounted_price and list_price:
                discount_pct = round((1 - discounted_price / list_price) * 100, 2)

        # Precio efectivo: con descuento si hay oferta, sino precio de lista
        actual_price = discounted_price if (on_sale and discounted_price) else list_price

        # Categoría y unidad
        groups = data.get("groups") or []
        category = map_category(groups)
        unit = map_unit(
            data.get("product_format", ""),
            data.get("product_unit_of_measure", ""),
        )
        qty_num = data.get("product_format_quantity") or 0
        quantity = build_quantity_str(qty_num, data.get("product_format", "")) if qty_num else None

        # El "id" de Constructor.io (ej. "prod00251876") es el SKU interno de
        # Coto, no un EAN/UPC real — Coto no expone código de barras real en
        # este endpoint. Se prefija para que is_real_barcode() nunca lo trate
        # como un barcode genuino (mismo criterio que la_anonima.py), así
        # entra siempre por el camino de alias/fuzzy matching en vez de crear
        # un producto aislado por cada SKU de 8 dígitos.
        raw_id = data.get("id", "")
        barcode = f"coto_{raw_id.removeprefix('prod')}" if raw_id else None

        # URL del producto en el sitio
        relative_url = data.get("url", "")
        url = f"{COTO_PRODUCT_URL_PREFIX}/{relative_url}" if relative_url else None

        return {
            "name": name,
            "normalized_name": normalize_product_name(name),
            "brand": data.get("product_brand"),
            "category": category,
            "unit": unit,
            "quantity": quantity,
            "image_url": data.get("image_url"),
            "barcode": barcode,
            "price": actual_price,
            "original_price": list_price if on_sale else None,
            "was_on_sale": on_sale,
            "discount_percentage": discount_pct,
            "url": url,
            "in_stock": bool(data.get("store_availability")),
        }

    def _save_product(self, db_session, product_data: dict) -> bool:
        """
        Obtiene o crea el Product (deduplicado por barcode/alias/fuzzy matching
        vía BaseScraper._get_or_create_product) y registra PriceHistory.
        Retorna True si el producto es nuevo.
        """
        barcode = product_data.get("barcode")
        product, is_new = self._get_or_create_product(db_session, barcode, "coto", product_data)

        db_session.add(PriceHistory(
            product_id=product.id,
            supermarket=Supermarket.COTO,
            price=product_data["price"],
            was_on_sale=product_data["was_on_sale"],
            original_price=product_data.get("original_price"),
            discount_percentage=product_data.get("discount_percentage"),
            url=product_data.get("url"),
            in_stock=product_data["in_stock"],
            province=self.default_province,
            region=self.default_region,
            city=self.default_city,
        ))
        return is_new

    def scrape(self, db_session=None, search_terms: list[str] = None, max_per_term: int = 200) -> int:
        """
        Ejecuta el scraping completo.
        - db_session=None → solo imprime (modo prueba)
        - db_session=<session> → guarda en DB
        Retorna cantidad de nuevos productos creados.
        """
        if search_terms is None:
            search_terms = ["leche", "aceite", "arroz", "fideos", "yerba"]

        total_new = 0

        for term in search_terms:
            page = 1
            term_count = 0
            total_results = None

            while True:
                remaining = max_per_term - term_count
                if remaining <= 0:
                    break

                print(f"[coto] Buscando: '{term}' (pág. {page})...")
                data = self.search(term, page=page, per_page=min(self.PER_PAGE, remaining))
                if not data:
                    break

                response = data.get("response", {})
                results = response.get("results") or []
                if total_results is None:
                    total_results = response.get("total_num_results", 0)

                if not results:
                    break

                batch_new = 0
                for result in results:
                    product_data = self.parse_product(result)
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

                # Avanzar página si quedan resultados
                if term_count >= (total_results or 0) or len(results) < self.PER_PAGE:
                    break
                page += 1

            print(f"[coto] '{term}': {term_count} productos procesados")

        return total_new


def _print_product(p: dict) -> None:
    """Imprime un producto en consola (modo prueba sin DB)."""
    price_str = f"${p['price']:,.2f}"
    if p["was_on_sale"] and p["original_price"]:
        price_str += f" (antes ${p['original_price']:,.2f}, -{p['discount_percentage']:.0f}%)"
    print(
        f"  ✓ {p['name'][:60]:<60} | {price_str} | "
        f"Marca: {p.get('brand') or '—'} | Cat: {p['category'].name}"
    )
