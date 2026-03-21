"""
Scraper de Chango Más (MasOnline) via API pública de VTEX.

Chango Más (GDN Argentina, ex-Walmart) usa VTEX, cuenta masonlineprod.
La estructura de la API es idéntica a Carrefour, Vea, Disco, Jumbo y Día
— hereda toda la lógica de CarrefourScraper.
"""
from app.config.settings import settings
from app.models.price_history import Supermarket
from app.scrapers.carrefour import CarrefourScraper, _VTEX_SEARCH_PATH


class ChangoMasScraper(CarrefourScraper):
    """
    Scraper de Chango Más / MasOnline.
    Hereda toda la lógica de CarrefourScraper — solo difiere en URLs y enum.
    """

    def __init__(self):
        super().__init__()
        self.name             = "chango_mas"
        self.search_url       = f"{settings.CHANGO_MAS_API_URL}{_VTEX_SEARCH_PATH}"
        self.store_url        = settings.CHANGO_MAS_STORE_URL
        self.supermarket_enum = Supermarket.CHANGO_MAS
