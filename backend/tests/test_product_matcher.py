"""
Pruebas unitarias para el matcher de productos por fuzzy matching (deduplicación).
No requiere DB real: se mockea la sesión de SQLAlchemy.
"""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.product_matcher import find_matching_product


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
