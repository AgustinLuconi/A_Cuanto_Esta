"""
Utilidad de fecha/hora compartida.
"""
from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    """
    UTC actual como datetime naive (sin tzinfo).

    Reemplaza datetime.utcnow() (deprecado desde Python 3.12) sin cambiar el
    esquema de la base: todas las columnas DateTime de este proyecto son
    naive (sin timezone=True) y se comparan/escriben como tal en todo el
    código. Usar datetime.now(timezone.utc) directamente reintroduciría el
    bug de comparar aware contra naive que ya se corrigió una vez.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
