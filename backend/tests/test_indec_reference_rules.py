"""
Pruebas de las reglas que emparejan un artículo del INDEC con productos de los
supermercados. Los nombres salen del catálogo real: para cada regla hay productos
que deben entrar y variantes que NO deben (orgánico, light, sin azúcar, gel...).
Se prefiere no emparejar a emparejar mal.
"""
import unicodedata

import pytest

from app.services.indec.reference_rules import RULES


def _norm(name: str) -> str:
    """Como `normalized_name` en la base: minúsculas y sin tildes."""
    stripped = unicodedata.normalize("NFKD", name)
    return "".join(c for c in stripped if not unicodedata.combining(c)).lower()


def _rule(label: str):
    return next(r for r in RULES if r.label == label)


CASES = {
    "Azúcar": (
        ["Azúcar La Campechana 1kg", "Azúcar Chango 1 Kg.", "Azúcar Ledesma molida superior bolsa 1 kg."],
        ["Azúcar Eritritol Pure Via 250g", "Gaseosa Tónica Sin Azúcar 354 Ml Schweppes",
         "Mermelada con Azúcar Frutilla Cuarto Creciente x 400 g.", "Azúcar Orgánica Beepure 700g"],
    ),
    "Arroz blanco (largo fino)": (
        ["Arroz Largo Fino Molinos Ala 500 Gr.", "ARROZ L.FINO MOCOVI BOLSA LAMINADO 1 KG"],
        ["ARROZ PARB. GALLO BOLSA 1 KG", "Arroz Egran Inflado 80 G", "Arroz Yamaní Gallo X500 Gr",
         "Alimento Adultos RAZA 3 Kg Pollo, Carne, Cereales Y Arroz"],
    ),
    "Harina de trigo": (
        ["Harina de Trigo 0000 Pureza x 1000 g.", "Harina 000 1 Kg Valle Fertil", "Harina De Trigo CHACABUCO 000 Paquete 1 Kg"],
        ["Harina Sagemuller Leudante", "Harina de Trigo Leudante 000 Pureza 1 Kg", "Harina de Maíz Pureza 500 g"],
    ),
    "Fideos secos": (
        ["Fideos Tirabuzón Favorita 500 Gr.", "Espagueti FAVORITA 500 Gr", "Fideos Matarazzo Spaghetti X500g"],
        ["Fideos Instantáneos Knorr 85 g", "Fideos Sin Tacc Dos Hermanos 500g", "Fideos Rellenos Verdura 500 g"],
    ),
    "Leche entera": (
        ["Leche Entera 3casanto 1l", "Leche Entera DIA Sachet 1 Lt.", "Leche Entera COTO Sachet 1 L"],
        ["Leche Entera en Polvo DIA 800 Gr.", "Leche Descremada La Serenísima 1 L", "Leche Entera Deslactosada 1 L"],
    ),
    "Aceite de girasol": (
        ["Aceite de girasol Pureza 1500 cc.", "ACEITE GIRASOL CAÑUELAS 1500 CC.", "Aceite De Girasol 1500ml Cuisine & Co"],
        ["Aceite de Oliva Extra Virgen 500 ml", "Aceite de girasol en aerosol 120 g", "Aceite de Girasol Alto Oleico 900ml"],
    ),
    "Manteca": (
        ["Manteca TONADITA 200 GRS", "Manteca Ilolay 100g", "Manteca PRIMER PREMIO 200g"],
        ["Manteca de maní Mani King 350g", "Mantecol Clásico 100 g", "Manteca sin lactosa 200 g"],
    ),
    "Dulce de leche": (
        ["Dulce De Leche Gandara 400g", "Dulce de Leche 450 Grs Vacalin", "Dulce De Leche Ser 400 G"],
        ["Dulce De Leche Beepure Sin Azúcar 400g", "Alfajor de dulce de leche 50 g", "Dulce de leche light 400 g"],
    ),
    "Lavandina": (
        ["Lavandina Querubín clásica 2 lt.", "LAVANDINA AYUDIN TRADICIONAL 2000 ML", "Lavandina Ayudín original 1 l."],
        ["Lavandina en Gel Original 1500 Ml Ayudín", "Limpiador con lavandina 500 ml"],
    ),
    "Gaseosa cola (Coca-Cola y Pepsi)": (
        ["Gaseosa Pepsi Vintage 1.5lt", "Gaseosa Coca Cola 1.5 L", "Coca-Cola Original 2.25 L"],
        ["Gaseosa Coca-Cola Zero 2.25 L", "Gaseosa Coca Cola Liviano 2.25l", "Gaseosa Manaos Cola 2.25 L",
         "Gaseosa Pepsi Black Sin Azúcar 1.5 L"],
    ),
    "Galletitas de agua": (
        ["Galletitas Crackers Dia 303 Gr.", "Galletitas De Agua Gran Agua Granix 600 Gr", "Galletitas crackers Criollitas 100 g."],
        ["Galletitas Crackers Integral Salvado 200 g", "Galletitas Dulces Anillos Terrabusi 170 Gr",
         "Galletitas de agua Sin Tacc 200 g"],
    ),
    "Galletitas dulces": (
        ["Galletitas Dulces Anillos Terrabusi 170 Gr", "Galletitas vainilla Porteñitas 139 g.", "Galletitas Vainilla Kukinas 180 Gr."],
        ["Galletitas Surtidas Bagley 400 Gr.", "Galletitas Dulces Rellenas Oreo 118 g", "Galletitas Dulces Sin Tacc 150 g",
         "Galletitas Crackers Dia 303 Gr."],
    ),
    "Queso cremoso": (
        ["Queso Cremoso Horma Puyehue X Kg", "Queso Cremoso Silvia 500 G", "Queso cremoso Classic x kg."],
        ["Queso Cremoso Light Casancrem 300 g", "Queso cremoso untable Casancrem 290 g", "Queso Crema Philadelphia 200 g"],
    ),
}


def test_every_rule_has_cases_so_none_is_untested():
    assert {r.label for r in RULES} == set(CASES)


def test_indec_codes_are_unique():
    codes = [r.indec_code for r in RULES]
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("label, name", [(l, n) for l, (good, _) in CASES.items() for n in good])
def test_rule_matches_equivalent_products(label, name):
    assert _rule(label).matches(_norm(name)), f"{label} debería incluir: {name}"


@pytest.mark.parametrize("label, name", [(l, n) for l, (_, bad) in CASES.items() for n in bad])
def test_rule_rejects_non_equivalent_products(label, name):
    assert not _rule(label).matches(_norm(name)), f"{label} NO debería incluir: {name}"
