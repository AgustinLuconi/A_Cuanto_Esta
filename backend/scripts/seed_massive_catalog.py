"""
Seeder masivo de productos y precios para todas las categorías del catálogo.
Genera productos de marcas argentinas populares con precios comparativos
en los 9 supermercados monitoreados.

Uso:
    cd backend
    source venv/bin/activate
    python scripts/seed_massive_catalog.py
"""
import sys
import os
import random
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.utils.normalizer import normalize_product_name


CATALOG_ITEMS = [
    # --- MASCOTAS ---
    {
        "name": "Alimento Seco Perro Raza Mediana y Grande Adulto 15kg",
        "brand": "Pedigree",
        "category": ProductCategory.MASCOTAS,
        "unit": ProductUnit.KG,
        "quantity": "15",
        "base_price": 42000.0,
        "barcode": "7791001001",
        "image_url": "https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?w=300",
    },
    {
        "name": "Alimento Seco Gato Adulto Control de Bolas de Pelo 7.5kg",
        "brand": "Cat Chow",
        "category": ProductCategory.MASCOTAS,
        "unit": ProductUnit.KG,
        "quantity": "7.5",
        "base_price": 28900.0,
        "barcode": "7791001002",
        "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=300",
    },
    {
        "name": "Snack Golosina Perro DentaStix Cuidado Oral x 7 u",
        "brand": "Pedigree",
        "category": ProductCategory.MASCOTAS,
        "unit": ProductUnit.PACK,
        "quantity": "7",
        "base_price": 3850.0,
        "barcode": "7791001003",
        "image_url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=300",
    },
    {
        "name": "Pouch Alimento Húmedo Gato Sabor Salmón 85g",
        "brand": "Purina Felix",
        "category": ProductCategory.MASCOTAS,
        "unit": ProductUnit.G,
        "quantity": "85",
        "base_price": 1350.0,
        "barcode": "7791001004",
        "image_url": "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=300",
    },

    # --- BEBES ---
    {
        "name": "Pañales Premium Care Talle XG (11-15kg) Pack x 44 u",
        "brand": "Pampers",
        "category": ProductCategory.BEBES,
        "unit": ProductUnit.PACK,
        "quantity": "44",
        "base_price": 26900.0,
        "barcode": "7792001001",
        "image_url": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=300",
    },
    {
        "name": "Pañales Triple Protección Talle M (5.5-9.5kg) x 48 u",
        "brand": "Huggies",
        "category": ProductCategory.BEBES,
        "unit": ProductUnit.PACK,
        "quantity": "48",
        "base_price": 21500.0,
        "barcode": "7792001002",
        "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=300",
    },
    {
        "name": "Shampoo Infantil Hipoalergénico No Más Lágrimas 400ml",
        "brand": "Johnson's Baby",
        "category": ProductCategory.BEBES,
        "unit": ProductUnit.ML,
        "quantity": "400",
        "base_price": 4900.0,
        "barcode": "7792001003",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
    },
    {
        "name": "Óleo Calcáreo con Manzanilla para Bebé 500ml",
        "brand": "Estrella Baby",
        "category": ProductCategory.BEBES,
        "unit": ProductUnit.ML,
        "quantity": "500",
        "base_price": 3750.0,
        "barcode": "7792001004",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
    },

    # --- HOGAR Y BAZAR ---
    {
        "name": "Bolsas de Residuo Negras Reforzadas 45x60cm x 30 u",
        "brand": "Asurin",
        "category": ProductCategory.HOGAR_BAZAR,
        "unit": ProductUnit.PACK,
        "quantity": "30",
        "base_price": 2650.0,
        "barcode": "7793001001",
        "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=300",
    },
    {
        "name": "Film Adherente Transparente de Cocina 30m",
        "brand": "Rolopack",
        "category": ProductCategory.HOGAR_BAZAR,
        "unit": ProductUnit.UNIDAD,
        "quantity": "1",
        "base_price": 2100.0,
        "barcode": "7793001002",
        "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=300",
    },
    {
        "name": "Papel Aluminio Extra Resistente 30cm x 5m",
        "brand": "Rolopack",
        "category": ProductCategory.HOGAR_BAZAR,
        "unit": ProductUnit.UNIDAD,
        "quantity": "1",
        "base_price": 2400.0,
        "barcode": "7793001003",
        "image_url": "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?w=300",
    },
    {
        "name": "Esponja Doble Uso Clásica Verde y Amarilla Pack x 3 u",
        "brand": "Mortimer",
        "category": ProductCategory.HOGAR_BAZAR,
        "unit": ProductUnit.PACK,
        "quantity": "3",
        "base_price": 1950.0,
        "barcode": "7793001004",
        "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=300",
    },

    # --- FARMACIA Y SALUD ---
    {
        "name": "Agua Oxigenada 10 Volúmenes Medicinal 250ml",
        "brand": "Bialcohol",
        "category": ProductCategory.FARMACIA_SALUD,
        "unit": ProductUnit.ML,
        "quantity": "250",
        "base_price": 1650.0,
        "barcode": "7794001001",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
    },
    {
        "name": "Algodón Hidrófilo Clásico Zig Zag 100g",
        "brand": "Estrella",
        "category": ProductCategory.FARMACIA_SALUD,
        "unit": ProductUnit.G,
        "quantity": "100",
        "base_price": 1890.0,
        "barcode": "7794001002",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
    },
    {
        "name": "Gasas Estériles en Sobres Individuales x 10 u",
        "brand": "Droguería",
        "category": ProductCategory.FARMACIA_SALUD,
        "unit": ProductUnit.PACK,
        "quantity": "10",
        "base_price": 2100.0,
        "barcode": "7794001003",
        "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
    },

    # --- ELECTRO Y TECNOLOGÍA ---
    {
        "name": "Cafetera de Filtro Eléctrica 1.2L 800W",
        "brand": "Oster",
        "category": ProductCategory.ELECTRO_TECNOLOGIA,
        "unit": ProductUnit.UNIDAD,
        "quantity": "1",
        "base_price": 54000.0,
        "barcode": "7795001001",
        "image_url": "https://images.unsplash.com/photo-1594212699903-ec8a3eca50f6?w=300",
    },
    {
        "name": "Licuadora con Jarra de Vidrio 1.5L 600W",
        "brand": "Liliana",
        "category": ProductCategory.ELECTRO_TECNOLOGIA,
        "unit": ProductUnit.UNIDAD,
        "quantity": "1",
        "base_price": 48500.0,
        "barcode": "7795001002",
        "image_url": "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=300",
    },
    {
        "name": "Sandwichera Eléctrica Placas Antiadherentes 750W",
        "brand": "Yelmo",
        "category": ProductCategory.ELECTRO_TECNOLOGIA,
        "unit": ProductUnit.UNIDAD,
        "quantity": "1",
        "base_price": 36000.0,
        "barcode": "7795001003",
        "image_url": "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=300",
    },

    # --- CARNES ---
    {
        "name": "Asado de Tira Vacuno Especial x 1kg",
        "brand": "Carnicería",
        "category": ProductCategory.CARNES,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 8900.0,
        "barcode": "7796001001",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=300",
    },
    {
        "name": "Pechuga de Pollo Fresca sin Piel x 1kg",
        "brand": "Granja Tres Arroyos",
        "category": ProductCategory.CARNES,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 6800.0,
        "barcode": "7796001002",
        "image_url": "https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=300",
    },
    {
        "name": "Carne Picada Especial Vacuna 1kg",
        "brand": "Carnicería",
        "category": ProductCategory.CARNES,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 6400.0,
        "barcode": "7796001003",
        "image_url": "https://images.unsplash.com/photo-1588168333986-5078d3ae3976?w=300",
    },
    {
        "name": "Vacío Vacuno Selección x 1kg",
        "brand": "Carnicería",
        "category": ProductCategory.CARNES,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 9800.0,
        "barcode": "7796001004",
        "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947?w=300",
    },

    # --- CONGELADOS ---
    {
        "name": "Hamburguesas Clásicas de Carne Vacuna x 4 u (332g)",
        "brand": "Paty",
        "category": ProductCategory.CONGELADOS,
        "unit": ProductUnit.PACK,
        "quantity": "4",
        "base_price": 4650.0,
        "barcode": "7797001001",
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300",
    },
    {
        "name": "Nuggets de Pollo Crocantes Rebozados 380g",
        "brand": "Sadia",
        "category": ProductCategory.CONGELADOS,
        "unit": ProductUnit.G,
        "quantity": "380",
        "base_price": 4200.0,
        "barcode": "7797001002",
        "image_url": "https://images.unsplash.com/photo-1562967914-608f82629710?w=300",
    },
    {
        "name": "Medallones de Merluza Rebozados x 4 u 400g",
        "brand": "Lucchetti",
        "category": ProductCategory.CONGELADOS,
        "unit": ProductUnit.G,
        "quantity": "400",
        "base_price": 4900.0,
        "barcode": "7797001003",
        "image_url": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=300",
    },
    {
        "name": "Papas Fritas Congeladas Corte Tradicional 700g",
        "brand": "McCain",
        "category": ProductCategory.CONGELADOS,
        "unit": ProductUnit.G,
        "quantity": "700",
        "base_price": 3800.0,
        "barcode": "7797001004",
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=300",
    },

    # --- FRUTAS Y VERDURAS ---
    {
        "name": "Banana Cavendish Seleccionada x 1kg",
        "brand": "Verdulería",
        "category": ProductCategory.FRUTAS_VERDURAS,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 2200.0,
        "barcode": "7798001001",
        "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=300",
    },
    {
        "name": "Manzana Roja Deliciosa Seleccionada x 1kg",
        "brand": "Verdulería",
        "category": ProductCategory.FRUTAS_VERDURAS,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 2400.0,
        "barcode": "7798001002",
        "image_url": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=300",
    },
    {
        "name": "Papa Negra Lavada x 1kg",
        "brand": "Verdulería",
        "category": ProductCategory.FRUTAS_VERDURAS,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 1100.0,
        "barcode": "7798001003",
        "image_url": "https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=300",
    },
    {
        "name": "Tomate Redondo Seleccionado x 1kg",
        "brand": "Verdulería",
        "category": ProductCategory.FRUTAS_VERDURAS,
        "unit": ProductUnit.KG,
        "quantity": "1",
        "base_price": 2600.0,
        "barcode": "7798001004",
        "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=300",
    },

    # --- PANADERÍA ---
    {
        "name": "Pan Lactal Blanco Clásico 550g",
        "brand": "Bimbo",
        "category": ProductCategory.PANADERIA,
        "unit": ProductUnit.G,
        "quantity": "550",
        "base_price": 3200.0,
        "barcode": "7799001001",
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300",
    },
    {
        "name": "Pan de Salvado Doble Fibra 550g",
        "brand": "Fargo",
        "category": ProductCategory.PANADERIA,
        "unit": ProductUnit.G,
        "quantity": "550",
        "base_price": 3450.0,
        "barcode": "7799001002",
        "image_url": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300",
    },
    {
        "name": "Tapas para Empanadas Criollas Hojaldradas x 12 u",
        "brand": "La Salteña",
        "category": ProductCategory.PANADERIA,
        "unit": ProductUnit.PACK,
        "quantity": "12",
        "base_price": 1950.0,
        "barcode": "7799001003",
        "image_url": "https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?w=300",
    },
    {
        "name": "Tapa para Tarta Pascualina Hojaldre x 2 u (400g)",
        "brand": "La Salteña",
        "category": ProductCategory.PANADERIA,
        "unit": ProductUnit.PACK,
        "quantity": "2",
        "base_price": 2300.0,
        "barcode": "7799001004",
        "image_url": "https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?w=300",
    },
]

SUPERMARKETS = [
    Supermarket.CARREFOUR,
    Supermarket.COTO,
    Supermarket.DISCO,
    Supermarket.JUMBO,
    Supermarket.VEA,
    Supermarket.DIA,
    Supermarket.ATOMO,
    Supermarket.LA_ANONIMA,
    Supermarket.CHANGO_MAS,
]


def seed():
    session = SessionLocal()
    try:
        created_count = 0
        updated_count = 0
        prices_count = 0

        now = datetime.now(timezone.utc)

        for item in CATALOG_ITEMS:
            prod = session.query(Product).filter(Product.barcode == item["barcode"]).first()
            if not prod:
                prod = Product(
                    name=item["name"],
                    normalized_name=normalize_product_name(item["name"]),
                    brand=item["brand"],
                    category=item["category"],
                    unit=item["unit"],
                    quantity=item["quantity"],
                    barcode=item["barcode"],
                    image_url=item["image_url"],
                    description=f"Producto relevado de la categoría {item['category'].value}",
                )
                session.add(prod)
                session.commit()
                session.refresh(prod)
                created_count += 1
            else:
                updated_count += 1

            # Generar precios en los 9 supermercados
            base_p = item["base_price"]

            for sm in SUPERMARKETS:
                # Variación entre supermercados (±12%)
                multiplier = random.uniform(0.88, 1.12)
                price = round(base_p * multiplier, 2)
                on_sale = random.choice([True, False, False, False])
                orig_price = round(price * random.uniform(1.15, 1.30), 2) if on_sale else None
                disc_pct = round((1 - price / orig_price) * 100, 1) if orig_price else None

                ph = PriceHistory(
                    product_id=prod.id,
                    supermarket=sm,
                    price=price,
                    was_on_sale=on_sale,
                    original_price=orig_price,
                    discount_percentage=disc_pct,
                    in_stock=random.choice([True, True, True, False]),
                    scraped_at=now,
                    url=f"https://www.{sm.value}.com.ar/product/{prod.id}",
                )
                session.add(ph)
                prices_count += 1

        session.commit()
        print(f"✅ Seeder masivo exitoso: {created_count} nuevos productos creados, {prices_count} precios guardados.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error durante el seeding masivo: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
