"""
Clase base abstracta para todos los scrapers del proyecto.
Define la interfaz común y manejo de HTTP/delays.
"""
import time
from abc import ABC, abstractmethod

import requests

from app.config.settings import settings


class BaseScraper(ABC):
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.USER_AGENT})
        self.delay = settings.SCRAPING_DELAY
        self.timeout = settings.SCRAPING_TIMEOUT

    def _get(self, url: str, params: dict = None) -> dict | None:
        """GET con manejo de errores y delay post-request."""
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            print(f"[scraper] HTTP {e.response.status_code} en {url}")
            return None
        except requests.RequestException as e:
            print(f"[scraper] Error de red en {url}: {e}")
            return None
        finally:
            time.sleep(self.delay)

    @abstractmethod
    def scrape(self, **kwargs) -> int:
        """Ejecuta el scraping completo. Retorna cantidad de nuevos productos."""
        ...

    @abstractmethod
    def parse_product(self, raw: dict) -> dict | None:
        """Convierte un item crudo de la API/HTML en un dict normalizado para DB."""
        ...
