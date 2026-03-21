"""
Enums de ubicación geográfica para Argentina.
Usados para validación en código — en DB se almacenan como String (más flexible).
"""
from enum import Enum


class Region(str, Enum):
    """Regiones geográficas de Argentina"""
    AMBA = "amba"
    PAMPEANA = "pampeana"
    CUYO = "cuyo"
    NOA = "noa"
    NEA = "nea"
    PATAGONIA = "patagonia"
    CENTRO = "centro"


class Province(str, Enum):
    """Provincias de Argentina"""
    CABA = "caba"
    BUENOS_AIRES = "buenos_aires"
    CORDOBA = "cordoba"
    SANTA_FE = "santa_fe"
    MENDOZA = "mendoza"
    SAN_JUAN = "san_juan"
    SAN_LUIS = "san_luis"
    SALTA = "salta"
    JUJUY = "jujuy"
    TUCUMAN = "tucuman"
    CATAMARCA = "catamarca"
    SANTIAGO_DEL_ESTERO = "santiago_del_estero"
    MISIONES = "misiones"
    CORRIENTES = "corrientes"
    CHACO = "chaco"
    FORMOSA = "formosa"
    NEUQUEN = "neuquen"
    RIO_NEGRO = "rio_negro"
    CHUBUT = "chubut"
    SANTA_CRUZ = "santa_cruz"
    TIERRA_DEL_FUEGO = "tierra_del_fuego"
    LA_PAMPA = "la_pampa"
    ENTRE_RIOS = "entre_rios"
    LA_RIOJA = "la_rioja"


REGION_PROVINCES = {
    Region.AMBA: [Province.CABA, Province.BUENOS_AIRES],
    Region.PAMPEANA: [Province.BUENOS_AIRES, Province.SANTA_FE, Province.CORDOBA,
                      Province.LA_PAMPA, Province.ENTRE_RIOS],
    Region.CUYO: [Province.MENDOZA, Province.SAN_JUAN, Province.SAN_LUIS],
    Region.NOA: [Province.SALTA, Province.JUJUY, Province.TUCUMAN,
                 Province.CATAMARCA, Province.SANTIAGO_DEL_ESTERO, Province.LA_RIOJA],
    Region.NEA: [Province.MISIONES, Province.CORRIENTES, Province.CHACO, Province.FORMOSA],
    Region.PATAGONIA: [Province.NEUQUEN, Province.RIO_NEGRO, Province.CHUBUT,
                       Province.SANTA_CRUZ, Province.TIERRA_DEL_FUEGO],
    Region.CENTRO: [Province.CORDOBA, Province.SANTA_FE],
}
