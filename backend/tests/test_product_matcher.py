"""
Pruebas unitarias para el matcher de productos por fuzzy matching (deduplicación).
No requiere DB real: se mockea la sesión de SQLAlchemy.
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.product_matcher import find_matching_product, _quantity_conflict, _variant_word_conflict


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
