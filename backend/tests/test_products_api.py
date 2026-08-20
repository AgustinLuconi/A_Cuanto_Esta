"""
Pruebas de integración para los endpoints de productos (/api/v1/products).
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_products_success():
    response = client.get("/api/v1/products?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_list_products_filter_by_category():
    response = client.get("/api/v1/products?category=mascotas")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["category"] in ["mascotas", "MASCOTAS"]


def test_search_products_by_text():
    response = client.get("/api/v1/products/search?q=perro")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "supermarket_counts" in data
    assert "variation_counts" in data


def test_search_products_filter_by_supermarkets():
    response = client.get("/api/v1/products/search?q=alimento&supermarkets=coto&supermarkets=carrefour")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


def test_search_products_filter_only_on_sale():
    response = client.get("/api/v1/products/search?q=a&only_on_sale=true")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


def test_search_products_filter_only_in_stock():
    response = client.get("/api/v1/products/search?q=a&only_in_stock=true")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


def test_search_products_sort_by_price_asc():
    response = client.get("/api/v1/products/search?q=a&sort=price_asc")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["items"], list)


def test_get_product_facets():
    response = client.get("/api/v1/products/facets?q=alimento")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "mascotas" in data or "alimentos" in data


def test_count_products():
    response = client.get("/api/v1/products/count")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert isinstance(data["count"], int)


def test_get_product_detail_404_for_non_existent():
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{random_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Producto no encontrado"
