# 📚 Guía Paso a Paso: Configuración de Base de Datos con Alembic

## 🎯 Objetivo
Configurar PostgreSQL, Alembic y crear las tablas del proyecto (Product, PriceHistory, EconomicIndicator).

---

## 📋 Prerrequisitos

### 1. Instalar PostgreSQL
**Windows:**
```bash
# Descargar desde: https://www.postgresql.org/download/windows/
# Instalar con pgAdmin incluido
```

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Verificar instalación
```bash
psql --version
# Debería mostrar: psql (PostgreSQL) 14.x o superior
```

---

## 🗄️ Paso 1: Crear Base de Datos PostgreSQL

### Opción A: Usando psql (Terminal)
```bash
# Conectar a PostgreSQL como superusuario
sudo -u postgres psql

# Dentro de psql:
CREATE DATABASE acuantoesta;
CREATE USER acuanto_user WITH PASSWORD 'tu_password_segura';
GRANT ALL PRIVILEGES ON DATABASE acuantoesta TO acuanto_user;

# Salir
\q
```

### Opción B: Usando pgAdmin (GUI)
1. Abrir pgAdmin
2. Conectar al servidor PostgreSQL local
3. Click derecho en "Databases" → "Create" → "Database"
4. Nombre: `acuantoesta`
5. Click derecho en "Login/Group Roles" → "Create" → "Login/Group Role"
6. Nombre: `acuanto_user`
7. Tab "Definition" → Password: `tu_password_segura`
8. Tab "Privileges" → Can login: Yes

---

## ⚙️ Paso 2: Configurar Variables de Entorno

### Crear archivo .env en /backend/
```bash
cd backend
cp .env.example .env
```

### Editar .env con tus datos
```env
# Database Configuration
DATABASE_URL=postgresql://acuanto_user:tu_password_segura@localhost:5432/acuantoesta
DATABASE_ECHO=False

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=A Cuanto Está
VERSION=1.0.0
DEBUG=True

# CORS Configuration
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Redis Configuration (dejar por ahora)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Scraping Configuration
SCRAPING_DELAY=2
SCRAPING_TIMEOUT=30
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# External APIs
ARGENTINA_DATOS_API_URL=https://api.argentinadatos.com
DATOS_GOB_AR_API_URL=https://apis.datos.gob.ar/series/api

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Cache Configuration
CACHE_TTL=3600
PRICE_CACHE_TTL=1800

# Security (CAMBIAR EN PRODUCCIÓN)
SECRET_KEY=dev-secret-key-cambiar-en-produccion-12345678

# Environment
ENVIRONMENT=development
```

**⚠️ IMPORTANTE:** Asegúrate de que la URL de la base de datos coincida con tus credenciales.

---

## 📦 Paso 3: Instalar Dependencias

### Crear entorno virtual
```bash
cd backend
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### Instalar paquetes
```bash
pip install -r requirements.txt
```

### Verificar instalación
```bash
python -c "import fastapi; import sqlalchemy; import alembic; print('✅ Todo instalado correctamente')"
```

---

## 🔧 Paso 4: Crear Primera Migración con Alembic

### Inicializar Alembic (ya está configurado, pero por si acaso)
```bash
# Esto ya está hecho, NO ejecutar de nuevo:
# alembic init alembic
```

### Crear migración inicial automática
```bash
alembic revision --autogenerate -m "Initial migration: create products, price_history, and economic_indicators tables"
```

**Esto creará un archivo en:** `alembic/versions/xxxx_initial_migration.py`

### Revisar el archivo de migración generado
```bash
# Abrir en Claude Code el archivo más reciente en alembic/versions/
# Debería contener:
# - create_table('products')
# - create_table('price_history')
# - create_table('economic_indicators')
# - Índices y foreign keys
```

---

## 🚀 Paso 5: Ejecutar Migraciones

### Aplicar migración a la base de datos
```bash
alembic upgrade head
```

**Salida esperada:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, Initial migration
```

### Verificar estado de migraciones
```bash
alembic current
```

---

## ✅ Paso 6: Verificar Tablas Creadas

### Opción A: Usando psql
```bash
psql -U acuanto_user -d acuantoesta

# Listar tablas
\dt

# Ver estructura de una tabla
\d products
\d price_history
\d economic_indicators

# Salir
\q
```

**Deberías ver:**
- `alembic_version` (tabla de control de Alembic)
- `products`
- `price_history`
- `economic_indicators`

### Opción B: Usando pgAdmin
1. Abrir pgAdmin
2. Navegar a: Servers → PostgreSQL → Databases → acuantoesta → Schemas → public → Tables
3. Verificar que existan las 4 tablas

---

## 🧪 Paso 7: Probar Conexión desde FastAPI

### Crear script de prueba
Crear archivo `backend/test_db.py`:

```python
"""
Script de prueba para verificar conexión a base de datos
"""
from app.config.database import SessionLocal, engine
from app.models import Product, PriceHistory, EconomicIndicator
from app.models.product import ProductCategory, ProductUnit
from app.models.price_history import Supermarket
from app.models.economic_indicator import IndicatorType, DataSource
from datetime import datetime, date
from decimal import Decimal

def test_connection():
    """Probar conexión y crear datos de prueba"""
    db = SessionLocal()
    
    try:
        # Crear producto de prueba
        product = Product(
            name="Aceite de Girasol",
            normalized_name="aceite girasol",
            brand="Cocinero",
            category=ProductCategory.ALIMENTOS,
            unit=ProductUnit.ML,
            quantity="900",
            description="Aceite de girasol 900ml"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        print(f"✅ Producto creado: {product.full_name} (ID: {product.id})")
        
        # Crear precio de prueba
        price = PriceHistory(
            product_id=product.id,
            supermarket=Supermarket.CARREFOUR,
            price=Decimal("2500.50"),
            was_on_sale=False,
            in_stock=True,
            url="https://www.carrefour.com.ar/aceite-test"
        )
        db.add(price)
        db.commit()
        
        print(f"✅ Precio creado: ${price.price} en {price.supermarket.value}")
        
        # Crear indicador económico de prueba
        indicator = EconomicIndicator(
            indicator_type=IndicatorType.INFLATION_MONTHLY,
            value=Decimal("2.8"),
            date=date.today(),
            source=DataSource.INDEC
        )
        db.add(indicator)
        db.commit()
        
        print(f"✅ Indicador creado: {indicator.indicator_type.value} = {indicator.value}%")
        
        # Consultar datos
        products_count = db.query(Product).count()
        prices_count = db.query(PriceHistory).count()
        indicators_count = db.query(EconomicIndicator).count()
        
        print(f"\n📊 Base de datos:")
        print(f"   - Productos: {products_count}")
        print(f"   - Precios: {prices_count}")
        print(f"   - Indicadores: {indicators_count}")
        
        print("\n🎉 ¡Base de datos configurada correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()
```

### Ejecutar prueba
```bash
cd backend
python test_db.py
```

**Salida esperada:**
```
✅ Producto creado: Cocinero Aceite de Girasol (900 ml) (ID: ...)
✅ Precio creado: $2500.50 en carrefour
✅ Indicador creado: inflation_monthly = 2.8%

📊 Base de datos:
   - Productos: 1
   - Precios: 1
   - Indicadores: 1

🎉 ¡Base de datos configurada correctamente!
```

---

## 🛠️ Comandos Útiles de Alembic

### Ver historial de migraciones
```bash
alembic history
```

### Ver migración actual
```bash
alembic current
```

### Crear nueva migración (después de cambiar modelos)
```bash
alembic revision --autogenerate -m "Descripción del cambio"
```

### Aplicar migraciones
```bash
alembic upgrade head
```

### Revertir última migración
```bash
alembic downgrade -1
```

### Revertir todas las migraciones
```bash
alembic downgrade base
```

### Aplicar migración específica
```bash
alembic upgrade <revision_id>
```

---

## ❓ Solución de Problemas

### Error: "could not connect to server"
```bash
# Verificar que PostgreSQL esté corriendo
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# Iniciar PostgreSQL
sudo systemctl start postgresql  # Linux
brew services start postgresql@14  # macOS
```

### Error: "FATAL: password authentication failed"
- Verificar credenciales en archivo .env
- Verificar que el usuario tenga permisos en la base de datos

### Error: "database does not exist"
```bash
# Crear base de datos manualmente
createdb -U postgres acuantoesta
```

### Error: "No module named 'app'"
```bash
# Asegurarse de estar en la carpeta backend/
cd backend

# Verificar que existe app/__init__.py
ls app/__init__.py
```

### Error en Alembic: "Target database is not up to date"
```bash
# Ver estado actual
alembic current

# Aplicar migraciones pendientes
alembic upgrade head
```

---

## ✅ Checklist Final

- [ ] PostgreSQL instalado y corriendo
- [ ] Base de datos `acuantoesta` creada
- [ ] Usuario `acuanto_user` creado con permisos
- [ ] Archivo .env configurado con credenciales correctas
- [ ] Dependencias instaladas (requirements.txt)
- [ ] Primera migración creada
- [ ] Migraciones aplicadas (alembic upgrade head)
- [ ] Tablas verificadas en PostgreSQL
- [ ] Script de prueba ejecutado correctamente

---

## 🎯 Próximos Pasos

Una vez completado esto, estarás listo para:
1. ✅ Crear cliente de ArgentinaDatos API
2. ✅ Desarrollar scrapers
3. ✅ Crear endpoints de FastAPI
4. ✅ Implementar lógica de negocio

---

## 📝 Notas Importantes

- **Nunca** commitear el archivo `.env` a Git (ya está en .gitignore)
- Cambiar `SECRET_KEY` en producción (usar: `openssl rand -hex 32`)
- Hacer backup de la base de datos regularmente
- Documentar cambios importantes en migraciones

---

**¿Problemas?** Contacta en este chat y resolveremos juntos.
