# 🛒 A Cuanto Está?

## Descripción

Plataforma de comparación de precios de productos en supermercados argentinos con análisis de contexto económico en tiempo real.

## 🎯 Objetivos del Proyecto

- **Comparación de precios**: Precios actuales de productos en múltiples supermercados
- **Historial de precios**: Seguimiento de evolución de precios en el tiempo
- **Contexto económico**: Integración con indicadores macroeconómicos (inflación, dólar, UVA)
- **Análisis inteligente**: Comparación de aumentos vs inflación general
- **Aprendizaje**: Web scraping, APIs, bases de datos, desarrollo full-stack

## 🏗️ Arquitectura

### Backend
- **Framework**: FastAPI (Python)
- **Base de datos**: PostgreSQL
- **Web Scraping**: BeautifulSoup4 + Selenium
- **Automatización**: Celery + Redis
- **APIs externas**: ArgentinaDatos, Datos.gob.ar

### Frontend
- **Framework**: React
- **Styling**: Tailwind CSS
- **Gráficos**: Recharts / Chart.js
- **State Management**: React Context / Zustand

## 📊 Fuentes de Datos

### Supermercados (Web Scraping)
1. Carrefour
2. Coto Digital
3. Disco

### Datos Económicos (APIs)
- **ArgentinaDatos API**: Inflación, dólar, tasas, índices
- **Datos.gob.ar**: IPC por categorías, datos oficiales

## 🚀 Características Principales

- ✅ Comparación de precios en tiempo real
- ✅ Historial de precios con gráficos
- ✅ Indicadores de tendencia (subió/bajó/estable)
- ✅ Contexto económico (inflación, dólar)
- ✅ Análisis: aumento vs inflación general
- ✅ Conversión a dólar (blue/oficial)
- ✅ Búsqueda y filtros avanzados
- ✅ API REST documentada

## 📁 Estructura del Proyecto
```
A_Cuanto_Esta?/
├── backend/           # API FastAPI + Scrapers
│   ├── app/
│   │   ├── api/       # Endpoints REST
│   │   ├── models/    # Modelos SQLAlchemy
│   │   ├── schemas/   # Schemas Pydantic
│   │   ├── scrapers/  # Web scrapers
│   │   ├── services/  # Lógica de negocio
│   │   └── config/    # Configuración
│   └── tests/         # Tests unitarios
├── frontend/          # React app
└── docs/              # Documentación
```

## 🛠️ Tecnologías

**Backend:**
- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic (migraciones)
- BeautifulSoup4
- Selenium
- Celery
- Redis
- PostgreSQL

**Frontend:**
- React 18
- Tailwind CSS
- React Router
- Recharts
- Axios

## 📦 Instalación

### Prerrequisitos
- Python 3.11+
- PostgreSQL 14+
- Node.js 18+
- Redis (para tareas programadas)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Crear base de datos
alembic upgrade head

# Ejecutar servidor
uvicorn app.main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 🗄️ Modelo de Datos

### Tablas Principales

**products**: Catálogo de productos normalizados
**price_history**: Historial completo de precios
**economic_indicators**: Indicadores económicos (inflación, dólar, etc)

Ver [DATABASE.md](docs/DATABASE.md) para esquema completo.

## 📚 Documentación

- [Arquitectura](docs/ARCHITECTURE.md)
- [Base de Datos](docs/DATABASE.md)
- [API Docs](docs/API_DOCS.md)

## 🎯 Roadmap

### Fase 1: Fundamentos ✅
- [x] Estructura del proyecto
- [x] Modelos de base de datos
- [x] Setup FastAPI
- [ ] Cliente ArgentinaDatos API
- [ ] Primer scraper funcional

### Fase 2: Scraping Completo
- [ ] Scrapers de 3 supermercados
- [ ] Normalización de datos
- [ ] Manejo de errores
- [ ] Sistema de logs

### Fase 3: Backend Completo
- [ ] API REST completa
- [ ] Endpoints de búsqueda/comparación
- [ ] Cache con Redis
- [ ] Documentación OpenAPI

### Fase 4: Frontend
- [ ] Interfaz de búsqueda
- [ ] Comparador de precios
- [ ] Gráficos de evolución
- [ ] Dashboard económico

### Fase 5: Automatización
- [ ] Scraping programado (Celery)
- [ ] Tareas automáticas
- [ ] Monitoreo y alertas

### Fase 6: Deployment
- [ ] Containerización (Docker)
- [ ] CI/CD
- [ ] Deploy a producción

## 📄 Licencia

MIT License

## 👨‍💻 Autor

Proyecto de aprendizaje - Web scraping, APIs y desarrollo full-stack

---

**Estado**: 🚧 En desarrollo activo