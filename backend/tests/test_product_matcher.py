"""
Pruebas unitarias para el matcher de productos por fuzzy matching (deduplicación).
No requiere DB real: se mockea la sesión de SQLAlchemy.
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.product_matcher import (
    find_matching_product,
    _quantity_conflict,
    _variant_word_conflict,
    find_strict_match_candidates,
    _significant_tokens,
)


def _make_candidate(normalized_name, brand=None, quantity=None):
    return SimpleNamespace(normalized_name=normalized_name, brand=brand, quantity=quantity)


def _db_with_candidates(candidates):
    """Mockea db.query(Product).filter(...).limit(50).all() -> candidates"""
    db = MagicMock()
    db.query.return_value.filter.return_value.limit.return_value.all.return_value = candidates
    return db


def test_returns_no_match_for_empty_normalized_name_without_querying_db():
    # Arrange: un nombre que normaliza a cadena vacía (solo puntuación/espacios)
    db = _db_with_candidates([_make_candidate("cualquier cosa")])

    # Act
    product, confidence = find_matching_product("---", None, None, None, db)

    # Assert
    assert (product, confidence) == (None, 0.0)
    db.query.assert_not_called()


def test_returns_no_match_when_prefilter_finds_no_candidates():
    # Arrange
    db = _db_with_candidates([])

    # Act
    product, confidence = find_matching_product("Leche Entera 1L", None, None, None, db)

    # Assert
    assert (product, confidence) == (None, 0.0)


def test_returns_no_match_when_best_score_below_threshold():
    # Arrange: un único candidato, score por debajo del umbral (85) y sin bonus
    candidate = _make_candidate("producto totalmente distinto")
    db = _db_with_candidates([candidate])

    with patch("app.services.product_matcher.fuzz.token_sort_ratio", return_value=84):
        product, confidence = find_matching_product("Leche Entera 1L", None, None, None, db)

    assert product is None
    assert confidence == 0.0


def test_brand_and_quantity_bonus_pushes_score_over_threshold():
    # Arrange: score base 80 (por debajo del umbral), pero brand y quantity coinciden
    # sumando +5 cada uno -> 90, por encima del umbral de 85.
    candidate = _make_candidate("leche entera", brand="Sancor", quantity="1L")
    db = _db_with_candidates([candidate])

    with patch("app.services.product_matcher.fuzz.token_sort_ratio", return_value=80):
        product, confidence = find_matching_product(
            "Leche Entera", "Sancor", "1L", None, db
        )

    assert product is candidate
    assert confidence == 0.9


def test_score_is_capped_at_100_even_with_bonuses():
    # Arrange: score base 98 + bonus de brand y quantity (10) superaría 100 sin el cap.
    candidate = _make_candidate("leche entera", brand="Sancor", quantity="1L")
    db = _db_with_candidates([candidate])

    with patch("app.services.product_matcher.fuzz.token_sort_ratio", return_value=98):
        product, confidence = find_matching_product(
            "Leche Entera", "Sancor", "1L", None, db
        )

    assert product is candidate
    assert confidence == 1.0  # 100 / 100, nunca > 1.0


def test_quantity_conflict_true_when_both_have_different_numbers():
    assert _quantity_conflict("agua de mesa nestle 500 ml", "agua de mesa nestle 2.25 l") is True


def test_quantity_conflict_false_when_numbers_match():
    assert _quantity_conflict("fideos mostachol n51 500 gr", "fideos mostachol n51 500 gr") is False


def test_quantity_conflict_false_when_either_side_has_no_number():
    assert _quantity_conflict("leche entera la serenisima", "leche entera la serenisima 1l") is False
    assert _quantity_conflict("leche entera la serenisima 1l", "leche entera la serenisima") is False


def test_high_score_match_rejected_when_quantities_conflict():
    # Arrange: score de texto altísimo (99), pero "700g" vs "1100g" son
    # presentaciones distintas -> no debería matchear pese al score.
    candidate = _make_candidate("papas corte tradicional simplot 1100g")
    db = _db_with_candidates([candidate])

    with patch("app.services.product_matcher.fuzz.token_sort_ratio", return_value=99):
        product, confidence = find_matching_product(
            "Papas Corte Tradicional Simplot 700g", None, None, None, db
        )

    assert (product, confidence) == (None, 0.0)


def test_variant_word_conflict_true_for_different_flavors():
    assert _variant_word_conflict("detergente bio active limon cif 500ml", "detergente bio active lima cif 500ml") is True


def test_variant_word_conflict_false_when_no_variant_words_present():
    assert _variant_word_conflict("leche entera la serenisima 1l", "leche descremada la serenisima 1l") is False


def test_high_score_match_rejected_when_flavor_words_conflict():
    # Arrange: score de texto altísimo (99) y misma cantidad, pero "limon" vs
    # "lima" son variantes distintas -> no debería matchear pese al score.
    candidate = _make_candidate("detergente bio active lima cif 500ml")
    db = _db_with_candidates([candidate])

    with patch("app.services.product_matcher.fuzz.token_sort_ratio", return_value=99):
        product, confidence = find_matching_product(
            "Detergente Bio Active Limon Cif 500ml", None, None, None, db
        )

    assert (product, confidence) == (None, 0.0)


def test_selects_highest_scoring_candidate_among_multiple():
    # Arrange: dos candidatos, el segundo tiene mejor score aunque aparezca después.
    low_candidate = _make_candidate("candidato bajo")
    high_candidate = _make_candidate("candidato alto")
    db = _db_with_candidates([low_candidate, high_candidate])

    with patch(
        "app.services.product_matcher.fuzz.token_sort_ratio",
        side_effect=[86, 95],
    ):
        product, confidence = find_matching_product("Producto X", None, None, None, db)

    assert product is high_candidate
    assert confidence == 0.95


# --- find_strict_match_candidates: matcher estructural para backfills ----


def _make_product(name, normalized_name, brand=None, category="OTROS", id_="p1"):
    return SimpleNamespace(id=id_, name=name, normalized_name=normalized_name, brand=brand, category=category)


def _db_returning(candidates):
    db = MagicMock()
    db.query.return_value.filter.return_value.limit.return_value.all.return_value = candidates
    return db


def test_significant_tokens_strips_brand_numbers_and_packaging_words():
    tokens = _significant_tokens("detergente magistral ultra limon botella 750ml", "magistral")
    assert tokens == {"detergente", "ultra", "limon"}


def test_significant_tokens_tokenizes_number_letter_and_spaced_forms_the_same():
    a = _significant_tokens("lavandina ayudin floral 700ml", "ayudin")
    b = _significant_tokens("lavandina ayudin floral 700 ml", "ayudin")
    assert a == b == {"lavandina", "floral"}


def test_significant_tokens_keeps_negation_words():
    # "sin"/"con"/"no" no son stopwords: invierten el significado del producto.
    sin = _significant_tokens("yogur sin azucar", None)
    con = _significant_tokens("yogur con azucar", None)
    assert "sin" in sin and "con" in con
    assert sin != con


def test_find_strict_match_candidates_matches_when_tokens_identical():
    product = _make_product("Detergente MAGISTRAL Ultra Limón 750ml", "detergente magistral ultra limon 750ml", brand="MAGISTRAL")
    candidate = _make_product("Detergente Magistral Ultra Limón 750 ml.", "detergente magistral ultra limon 750 ml", brand="Magistral", id_="p2")
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == [candidate]


def test_find_strict_match_candidates_rejects_brand_mismatch():
    product = _make_product("Gaseosa Cola COTO 1.5L", "gaseosa cola coto 1.5l", brand="COTO")
    candidate = _make_product("Gaseosa Cola PEPSI 1.5L", "gaseosa cola pepsi 1.5l", brand="PEPSI", id_="p2")
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == []


def test_find_strict_match_candidates_rejects_quantity_conflict():
    product = _make_product("Aceite COCINERO 1.5L", "aceite cocinero 1.5l", brand="COCINERO")
    candidate = _make_product("Aceite Cocinero 900ml", "aceite cocinero 900ml", brand="COCINERO", id_="p2")
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == []


def test_find_strict_match_candidates_rejects_when_extra_distinguishing_token():
    # "Triple Beneficio" vs "Triple Acción" -- líneas de producto distintas,
    # el token extra en cada lado ("beneficio" / "accion") rompe la igualdad exacta.
    product = _make_product(
        "Pasta Dental COLGATE Triple Beneficio 180g", "pasta dental colgate triple beneficio 180g", brand="COLGATE"
    )
    candidate = _make_product(
        "Pasta Dental Colgate Triple Acción 180g", "pasta dental colgate triple accion 180g", brand="Colgate", id_="p2"
    )
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == []


def test_find_strict_match_candidates_passes_through_when_brand_missing_on_one_side():
    # Sin marca de un lado, no se puede comparar por marca -- pero si los
    # tokens significativos coinciden igual, es un match válido (la marca ya
    # suele estar repetida dentro del nombre).
    product = _make_product("Manteca COTAMPO 200g", "manteca cotampo 200g", brand="COTAMPO")
    candidate = _make_product("Manteca Cotampo 200 G", "manteca cotampo 200 g", brand=None, id_="p2")
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == [candidate]


def test_find_strict_match_candidates_rejects_when_product_itself_has_no_brand():
    # Caso real encontrado en el backfill de Coto: "Leche Reducida en Lactosa
    # Sachet 1l" sin marca declarada -- no hay forma de confirmar que el
    # candidato (que sí declara marca) sea el mismo fabricante, así que no
    # se intenta ni matchear (aunque el candidato exista y sea plausible).
    product = _make_product("Leche Reducida En Lactosa Sachet 1l", "leche reducida en lactosa sachet 1l", brand=None)
    candidate = _make_product(
        "Leche Reducida en Lactosa Sachet La Serenisima x 1 Lt.",
        "leche reducida en lactosa sachet la serenisima x 1 lt", brand="LA SERENISIMA", id_="p2",
    )
    db = _db_returning([candidate])

    result = find_strict_match_candidates(product, db)

    assert result == []
    db.query.assert_not_called()


def test_find_strict_match_candidates_returns_empty_list_when_no_candidates():
    product = _make_product("Producto Único", "producto unico")
    db = _db_returning([])

    result = find_strict_match_candidates(product, db)

    assert result == []
