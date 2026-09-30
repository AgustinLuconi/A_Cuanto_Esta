"""
Pruebas unitarias para la lógica de matching de check_price_alerts.py.
No toca la DB ni pywebpush -- usa SimpleNamespace como en test_product_matcher.py.
"""
import os
import sys
from decimal import Decimal
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.check_price_alerts import _due_alerts


def _alert(product_id, target_price, notified_at_price=None):
    return SimpleNamespace(product_id=product_id, target_price=Decimal(str(target_price)), notified_at_price=(
        Decimal(str(notified_at_price)) if notified_at_price is not None else None
    ))


def _price(value, is_stale=False):
    return SimpleNamespace(price=Decimal(str(value)), is_stale=is_stale)


def test_alert_triggers_when_price_at_or_below_target():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(450)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 450.0)]


def test_alert_does_not_trigger_when_price_above_target():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(600)]}
    assert _due_alerts([alert], prices) == []


def test_alert_does_not_retrigger_at_same_notified_price():
    alert = _alert("p1", 500, notified_at_price=450)
    prices = {"p1": [_price(450)]}
    assert _due_alerts([alert], prices) == []


def test_alert_retriggers_when_price_drops_further():
    alert = _alert("p1", 500, notified_at_price=450)
    prices = {"p1": [_price(400)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 400.0)]


def test_alert_skipped_when_only_stale_prices_available():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(400, is_stale=True)]}
    assert _due_alerts([alert], prices) == []


def test_alert_uses_lowest_fresh_price_among_supermarkets():
    alert = _alert("p1", 500)
    prices = {"p1": [_price(480), _price(420), _price(999, is_stale=True)]}
    due = _due_alerts([alert], prices)
    assert due == [(alert, 420.0)]


def test_alert_skipped_when_product_has_no_price_data():
    alert = _alert("p1", 500)
    assert _due_alerts([alert], {}) == []
