"""
Cliente HTTP de la API del INDEC (https://api.indec.gob.ar).

Los datos se piden en `/v1/<slug>` (estilo PostgREST) con un token Bearer.
El servidor devuelve como máximo 1.000 filas por request, por eso `fetch`
pagina con `limit`/`offset`.

A diferencia de los clientes de ArgentinaDatos/DolarAPI, que devuelven una
lista vacía ante un error, este cliente LANZA excepciones: un job que termina
"en verde" con 0 filas es indistinguible de un día sin novedades.
"""
import base64
import json
import time
from datetime import datetime, timezone

import httpx

from app.config.settings import settings

# Se avisa cuando faltan menos días que estos para que venza el token
TOKEN_WARNING_DAYS = 30


class IndecError(Exception):
    """Error al consultar la API del INDEC."""


class IndecAuthError(IndecError):
    """Token ausente, inválido o vencido (401/403)."""


def token_days_remaining(token: str, now: datetime | None = None) -> int | None:
    """
    Días que faltan para que venza el JWT, leyendo el claim `exp` (sin verificar
    la firma). Devuelve None si el token no se puede decodificar.
    """
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        expires = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except (IndexError, ValueError, KeyError, TypeError):
        return None
    now = now or datetime.now(timezone.utc)
    return (expires - now).days


class IndecClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int = 3,
        retry_backoff: float = 1.0,
        page_size: int = 1000,
    ):
        self._token = token or settings.INDEC_API_TOKEN
        if not self._token:
            raise IndecAuthError("INDEC_API_TOKEN no está configurado")
        self.base_url = base_url or settings.INDEC_API_URL
        self.timeout = timeout or settings.SCRAPING_TIMEOUT
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.page_size = page_size

        days = token_days_remaining(self._token)
        if days is not None and days < TOKEN_WARNING_DAYS:
            print(f"[indec] ATENCIÓN: el token vence en {days} días, hay que renovarlo")

    def fetch(self, slug: str, params: dict[str, str], order: str) -> list[dict]:
        """
        Devuelve todas las filas del dataset `slug` que cumplen `params`
        (filtros PostgREST, ej. {"codigo": "in.(0,01)"}), paginando de a
        `page_size`. `order` debe ser un orden total para que las páginas no se
        solapen ni se salteen filas.
        """
        rows: list[dict] = []
        offset = 0
        while True:
            page = self._get_page(
                slug, {**params, "order": order, "limit": self.page_size, "offset": offset}
            )
            rows.extend(page)
            if len(page) < self.page_size:
                return rows
            offset += self.page_size

    def _get_page(self, slug: str, params: dict) -> list[dict]:
        """Pide una página con reintentos ante errores de red y 5xx."""
        url = f"{self.base_url}/v1/{slug}"
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        last_error = "sin detalle"
        for attempt in range(1, self.max_retries + 1):
            try:
                response = httpx.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    follow_redirects=True,
                )
            except httpx.HTTPError as e:
                last_error = f"error de red ({type(e).__name__})"
            else:
                status = response.status_code
                if status in (401, 403):
                    raise IndecAuthError(f"INDEC rechazó el token (HTTP {status}) en {slug}")
                if status >= 500:
                    last_error = f"HTTP {status}"
                elif status >= 400:
                    raise IndecError(f"INDEC respondió HTTP {status} en {slug}")
                else:
                    try:
                        data = response.json()
                    except ValueError:
                        raise IndecError(f"Respuesta inesperada de INDEC en {slug}: no es JSON")
                    if not isinstance(data, list):
                        raise IndecError(f"Respuesta inesperada de INDEC en {slug}: no es una lista")
                    return data
            print(f"[indec] {slug}: {last_error} (intento {attempt}/{self.max_retries})")
            if attempt < self.max_retries:
                time.sleep(self.retry_backoff * attempt)
        raise IndecError(f"INDEC no respondió en {slug} tras {self.max_retries} intentos: {last_error}")
