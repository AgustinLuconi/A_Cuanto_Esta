"""
Script standalone para poblar el catálogo de las 5 categorías nuevas:
mascotas, bebes, hogar_bazar, farmacia_salud, electro_tecnologia.

Uso:
    cd backend
    source venv/bin/activate
    python scripts/seed_expanded_catalog.py
"""
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.product import Product, ProductCategory, ProductUnit
from app.models.price_history import PriceHistory, Supermarket
from app.scrapers.utils.normalizer import normalize_product_name


EXPANDED_PRODUCTS = [
  # MASCOTAS
  {
    "name": "Alimento Seco Perro Adulto Carne y Vegetales 15kg",
    "brand": "Dog Chow",
    "category": ProductCategory.MASCOTAS,
    "unit": ProductUnit.KG,
    "quantity": "15",
    "base_price": 38500.0,
    "barcode": "761303100001",
    "image_url": "https://images.unsplash.com/photo-1568640347023-a616a30bc3bd?w=300",
  },
  {
    "name": "Alimento Húmedo Gato Pouch Atún 85g",
    "brand": "Whiskas",
    "category": ProductCategory.MASCOTAS,
    "unit": ProductUnit.G,
    "quantity": "85",
    "base_price": 1250.0,
    "barcode": "761303100002",
    "image_url": "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=300",
  },
  {
    "name": "Piedras Sanitarias Absorbentes para Gato 4kg",
    "brand": "Sanicat",
    "category": ProductCategory.MASCOTAS,
    "unit": ProductUnit.KG,
    "quantity": "4",
    "base_price": 5400.0,
    "barcode": "761303100003",
    "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=300",
  },

  # BEBES
  {
    "name": "Pañales Talle G (9-12.5kg) Pack x 52 u",
    "brand": "Pampers",
    "category": ProductCategory.BEBES,
    "unit": ProductUnit.PACK,
    "quantity": "52",
    "base_price": 24500.0,
    "barcode": "779000100001",
    "image_url": "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=300",
  },
  {
    "name": "Toallitas Húmedas Limpieza y Aloe Pack x 80 u",
    "brand": "Huggies",
    "category": ProductCategory.BEBES,
    "unit": ProductUnit.PACK,
    "quantity": "80",
    "base_price": 4200.0,
    "barcode": "779000100002",
    "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=300",
  },
  {
    "name": "Fórmula Infantil Etapa 1 de 0 a 6 Meses 800g",
    "brand": "Nutrilon",
    "category": ProductCategory.BEBES,
    "unit": ProductUnit.G,
    "quantity": "800",
    "base_price": 19800.0,
    "barcode": "779000100003",
    "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
  },

  # HOGAR & BAZAR
  {
    "name": "Papel de Cocina Doble Hoja Rollos x 3 u",
    "brand": "Elegante",
    "category": ProductCategory.HOGAR_BAZAR,
    "unit": ProductUnit.PACK,
    "quantity": "3",
    "base_price": 3100.0,
    "barcode": "779000200001",
    "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=300",
  },
  {
    "name": "Servilletas de Papel Blancas 33x33cm x 80 u",
    "brand": "Elite",
    "category": ProductCategory.HOGAR_BAZAR,
    "unit": ProductUnit.PACK,
    "quantity": "80",
    "base_price": 1850.0,
    "barcode": "779000200002",
    "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=300",
  },
  {
    "name": "Set de Contenedores Plásticos Herméticos x 4 u",
    "brand": "Bazar",
    "category": ProductCategory.HOGAR_BAZAR,
    "unit": ProductUnit.PACK,
    "quantity": "4",
    "base_price": 9500.0,
    "barcode": "779000200003",
    "image_url": "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?w=300",
  },

  # FARMACIA & SALUD
  {
    "name": "Alcohol En Gel Antibacterial con Válvula 500ml",
    "brand": "Bialcohol",
    "category": ProductCategory.FARMACIA_SALUD,
    "unit": ProductUnit.ML,
    "quantity": "500",
    "base_price": 3200.0,
    "barcode": "779000300001",
    "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
  },
  {
    "name": "Curitas Adhesivas Flexibles Caja x 20 u",
    "brand": "Band-Aid",
    "category": ProductCategory.FARMACIA_SALUD,
    "unit": ProductUnit.PACK,
    "quantity": "20",
    "base_price": 2800.0,
    "barcode": "779000300002",
    "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
  },

  # ELECTRO & TECNOLOGIA
  {
    "name": "Pava Eléctrica de Acero Inoxidable 1.7L 1850W",
    "brand": "Philips",
    "category": ProductCategory.ELECTRO_TECNOLOGIA,
    "unit": ProductUnit.UNIDAD,
    "quantity": "1",
    "base_price": 46000.0,
    "barcode": "779000400001",
    "image_url": "https://images.unsplash.com/photo-1594212699903-ec8a3eca50f6?w=300",
  },
  {
    "name": "Tostadora Eléctrica 2 Ranuras 800W",
    "brand": "Oster",
    "category": ProductCategory.ELECTRO_TECNOLOGIA,
    "unit": ProductUnit.UNIDAD,
    "quantity": "1",
    "base_price": 39500.0,
    "barcode": "779000400002",
    "image_url": "https://images.unsplash.com/photo-1583608205776-bfd35f0d9f83?w=300",
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
        prices_count = 0

        for item in EXPANDED_PRODUCTS:
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

            # Generar precios actuales e históricos para cada supermercado
            base_p = item["base_price"]
            now = datetime.utcnow()

            for sm in SUPERMARKETS:
                # Variación aleatoria de precio por supermercado (±15%)
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
        print(f"✅ Seeder ejecutado: {created_count} nuevos productos creados, {prices_count} precios guardados.")
    except Exception as e:
        session.rollback()
        print(f"❌ Error durante el seeding: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
