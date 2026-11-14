"""
Reglas que emparejan un artículo del INDEC con productos de los supermercados.

Cada regla dice, sobre `normalized_name` (minúsculas, sin tildes), qué productos
equivalen al artículo del INDEC. Se prefiere NO emparejar a emparejar mal: el
nombre debe EMPEZAR con el artículo (así "azúcar" no trae "gaseosa sin azúcar")
y se excluyen variantes que el INDEC no mide (orgánico, light, integral...).

No cubiertos por falta de productos en el catálogo (al 2026-11-14): yerba mate,
café molido y sal fina. Las reglas se agregan cuando haya al menos 3 ofertas.

Para sumar un artículo: agregar una `ReferenceRule` con el código del INDEC
(columna `series_code` de `indec_observations`, indicador "Precio promedio").
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ReferenceRule:
    indec_code: str
    label: str
    include: re.Pattern
    exclude: re.Pattern | None = None

    def matches(self, normalized_name: str) -> bool:
        if not self.include.search(normalized_name):
            return False
        return not (self.exclude and self.exclude.search(normalized_name))


def _rule(code: str, label: str, include: str, exclude: str | None = None) -> ReferenceRule:
    return ReferenceRule(
        indec_code=code,
        label=label,
        include=re.compile(include),
        exclude=re.compile(exclude) if exclude else None,
    )


RULES: tuple[ReferenceRule, ...] = (
    _rule("01.1.8.1.01", "Azúcar", r"^azucar\b",
          r"organic|eritritol|sucralosa|dietetic|light|rubi|mascab|mascav|impalpable|glas|stevia|edulcor|vainilla|sobre|saquit|cubo|terron|\bsin\b|negra|morena|\bcon\b"),
    _rule("01.1.1.3.01", "Arroz blanco (largo fino)", r"^arroz\b.*(largo fino|l\.? ?fino|\bfino\b)",
          r"yaman|integral|sushi|parb|parboil|inflado|basmati|salvaje|carolina|arborio|risotto|instant|alfajor|galleta|snack|chips|tortita|leche|polenta|saboriz|\bcon\b|cocid|vaporiz|doble|negro|jazmin|mix|premezcla"),
    _rule("01.1.1.3.11", "Harina de trigo", r"^harina( de)? (trigo|0000|000)\b|^harina (0000|000)\b",
          r"leudante|integral|pizza|maiz|almendra|arroz|avena|garbanzo|mezcla|preparad|sin tacc|reposteria|coco|centeno|soja|lenteja|espelta"),
    _rule("01.1.1.4.04", "Fideos secos", r"^(fideos|tirabuzon|tirabuzones|mostachol|tallarin|tallarines|spaghetti|espagueti|codito|municion|monito|rigatoni|fusilli|penne)\b",
          r"instant|sopa|sin tacc|integral|rellen|arroz|ramen|noodle|huevo|verdura|espinaca|tomate|remolacha|zanahoria|lentej|soja|quinoa|avena|vegetal|fresco|ravioles|sorrentino|capeletti"),
    _rule("01.1.4.1.01", "Leche entera", r"^leche (entera|fresca)\b|^leche .*\bentera\b",
          r"polvo|descremad|deslactos|sin lactosa|chocolat|cabra|avena|almendra|soja|coco|vegetal|condensad|evaporad|maternizad|infantil|crema|fortificad|cacao|vainilla|frutilla|dulce|bebida|barista|\bcon\b"),
    _rule("01.1.5.1.02", "Aceite de girasol", r"^aceite (de )?girasol\b",
          r"mezcla|oliva|alto oleico|spray|aerosol|ozono|cosmet|bebe|sabor|capsula|corporal|capilar|\bcon\b"),
    _rule("01.1.5.3.01", "Manteca", r"^manteca\b",
          r"mani|mantecol|cacao|chocolat|vegetal|karite|cerdo|ghee|light|sin lactosa|untable|cobertura|galleta|\bcon\b"),
    _rule("01.1.4.3.05", "Dulce de leche", r"^dulce de leche\b",
          r"alfajor|helado|galleta|postre|barra|snack|light|dietetic|chocolat|mini|sobre|sachet|pastelero|reposter|cobertura|bombon|\bsin\b|\bcon\b"),
    _rule("05.6.1.1.12", "Lavandina", r"^lavandina\b", r"\bgel\b|pastilla|tableta|polvo"),
    _rule("01.2.2.1.04", "Gaseosa cola (Coca-Cola y Pepsi)", r"^(gaseosa )?(coca[ -]?cola|pepsi)\b",
          r"zero|liviano|light|sin azucar|diet|vainilla|cherry|cereza|limon|lima|\blata\b|mini|\bx ?(6|12)\b|pack|\bsin\b|mix|sabor"),
)
