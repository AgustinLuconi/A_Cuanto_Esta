"""
Utilidad de fecha/hora compartida.
"""
from datetime import datetime, timezone


def utcnow_aware() -> datetime:
    """
    UTC actual, timezone-aware (tzinfo=UTC).

    Reemplaza datetime.utcnow() (deprecado desde Python 3.12). Todas las
    columnas DateTime del proyecto son timezone-aware (DateTime(timezone=True)),
    así que este es el único helper de "ahora" que debería usarse tanto para
    defaults de columnas como para comparaciones — no mezclar con datetimes
    naive, eso fue exactamente el bug que motivó unificar esto.
    """
    return datetime.now(timezone.utc)
