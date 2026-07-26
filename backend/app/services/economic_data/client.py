"""
Clientes HTTP para APIs económicas argentinas.
- ArgentinaDatosClient: datos históricos (argentinadatos.com)
- DolarAPIClient: cotizaciones en tiempo real (dolarapi.com)
"""
import httpx
from app.config.settings import settings
from app.services.economic_data.schemas import InflationRecord, DollarRecord, UVARecord, DolarAPIQuote


class ArgentinaDatosClient:
    def __init__(self):
        self.base_url = settings.ARGENTINA_DATOS_API_URL
        self.timeout = settings.SCRAPING_TIMEOUT

    def _get(self, endpoint: str) -> list | None:
        """Realiza GET y retorna el JSON parseado, o None si hay error."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[client] HTTP {e.response.status_code} en {url}")
            return None
        except httpx.HTTPError as e:
            print(f"[client] Error de red en {url}: {e}")
            return None

    def get_inflation(self) -> list[InflationRecord]:
        data = self._get("/v1/finanzas/indices/inflacion")
        if data is None:
            return []
        return [InflationRecord(**item) for item in data]

    def get_uva(self) -> list[UVARecord]:
        data = self._get("/v1/finanzas/indices/uva")
        if data is None:
            return []
        return [UVARecord(**item) for item in data]

    def get_inflation_yearly(self) -> list[InflationRecord]:
        """Retorna lista vacía si el endpoint no responde correctamente."""
        data = self._get("/v1/finanzas/indices/inflacionInteranual")
        if data is None:
            return []
        return [InflationRecord(**item) for item in data]

    def get_risk_country(self) -> list[InflationRecord]:
        """Riesgo país (EMBI+). Mismo shape que inflación: {fecha, valor}."""
        data = self._get("/v1/finanzas/indices/riesgo-pais")
        if data is None:
            return []
        return [InflationRecord(**item) for item in data]

    def get_all_dollars(self) -> list[DollarRecord]:
        """Histórico combinado de las 8 casas de cambio en una sola llamada."""
        data = self._get("/v1/cotizaciones/dolares")
        if data is None:
            return []
        return [DollarRecord(**item) for item in data]

    def get_estado(self) -> str | None:
        """
        Health-check propio de ArgentinaDatos. Devuelve el string de estado
        (ej. "Correcto") o None si el endpoint no respondió.
        """
        data = self._get("/v1/estado")
        if data is None:
            return None
        return data.get("estado")


class DolarAPIClient:
    """Cliente para dolarapi.com — cotizaciones en tiempo real."""

    def __init__(self):
        self.base_url = settings.DOLAR_API_URL
        self.timeout = settings.SCRAPING_TIMEOUT

    def _get(self, endpoint: str):
        """Realiza GET y retorna el JSON parseado, o None si hay error."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = httpx.get(url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[dolarapi] HTTP {e.response.status_code} en {url}")
            return None
        except httpx.HTTPError as e:
            print(f"[dolarapi] Error de red en {url}: {e}")
            return None

    def get_all_quotes(self) -> list[DolarAPIQuote]:
        """Obtiene todas las cotizaciones disponibles en un solo request."""
        data = self._get("/v1/dolares")
        if data is None:
            return []
        return [DolarAPIQuote(**item) for item in data]

    def get_quote(self, casa: str) -> DolarAPIQuote | None:
        """Obtiene la cotización de una casa específica (ej: 'blue', 'oficial')."""
        data = self._get(f"/v1/dolares/{casa}")
        if data is None:
            return None
        return DolarAPIQuote(**data)
