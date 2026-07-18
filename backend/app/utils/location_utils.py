"""
Utilidades para manejo de ubicaciones geográficas.
Mapeo inverso Province → Region y funciones de validación/display.
"""
import logging
from typing import Optional

from app.models.location import Province, Region

logger = logging.getLogger(__name__)

# Mapeo inverso: Provincia → Región primaria
# Buenos Aires: AMBA (primario) y PAMPEANA
# Córdoba, Santa Fe: PAMPEANA (primario) y CENTRO
PROVINCE_TO_REGION = {
    Province.CABA: Region.AMBA,
    Province.BUENOS_AIRES: Region.AMBA,
    Province.MENDOZA: Region.CUYO,
    Province.SAN_JUAN: Region.CUYO,
    Province.SAN_LUIS: Region.CUYO,
    Province.SALTA: Region.NOA,
    Province.JUJUY: Region.NOA,
    Province.TUCUMAN: Region.NOA,
    Province.CATAMARCA: Region.NOA,
    Province.SANTIAGO_DEL_ESTERO: Region.NOA,
    Province.LA_RIOJA: Region.NOA,
    Province.MISIONES: Region.NEA,
    Province.CORRIENTES: Region.NEA,
    Province.CHACO: Region.NEA,
    Province.FORMOSA: Region.NEA,
    Province.NEUQUEN: Region.PATAGONIA,
    Province.RIO_NEGRO: Region.PATAGONIA,
    Province.CHUBUT: Region.PATAGONIA,
    Province.SANTA_CRUZ: Region.PATAGONIA,
    Province.TIERRA_DEL_FUEGO: Region.PATAGONIA,
    Province.LA_PAMPA: Region.PAMPEANA,
    Province.SANTA_FE: Region.PAMPEANA,
    Province.CORDOBA: Region.PAMPEANA,
    Province.ENTRE_RIOS: Region.PAMPEANA,
}

_REGION_DISPLAY_NAMES = {
    "amba": "Área Metropolitana Buenos Aires",
    "cuyo": "Cuyo",
    "noa": "Noroeste Argentino",
    "nea": "Noreste Argentino",
    "patagonia": "Patagonia",
    "pampeana": "Región Pampeana",
    "centro": "Centro",
}


def get_region_from_province(province: str) -> Optional[str]:
    """Retorna el código de región para una provincia, o None."""
    if not province:
        return None
    try:
        prov_enum = Province(province.lower().strip())
        region = PROVINCE_TO_REGION.get(prov_enum)
        return region.value if region else None
    except ValueError:
        logger.warning(f"Provincia no reconocida: {province}")
        return None


def validate_location(province: str, region: str) -> bool:
    """Valida que una provincia pertenezca a la región. NULL es válido."""
    if not province or not region:
        return True
    expected = get_region_from_province(province)
    return expected == region.lower().strip() if expected else False


def get_province_display_name(province_code: str) -> str:
    """'buenos_aires' → 'Buenos Aires'"""
    if not province_code:
        return "Sin especificar"
    try:
        prov_enum = Province(province_code.lower())
        return prov_enum.name.replace("_", " ").title()
    except ValueError:
        return province_code.replace("_", " ").title()


def get_region_display_name(region_code: str) -> str:
    """'cuyo' → 'Cuyo', 'noa' → 'Noroeste Argentino'"""
    if not region_code:
        return "Sin especificar"
    return _REGION_DISPLAY_NAMES.get(region_code.lower(), region_code.title())
