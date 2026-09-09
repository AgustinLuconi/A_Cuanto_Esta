# Notificaciones push reales para alertas de precio

**Fecha:** 2026-09-09
**Estado:** Aprobado, pendiente de implementación

## Contexto

El sistema actual de alertas de precio (`frontend/src/lib/priceAlertsContext.tsx`,
`frontend/src/components/layout/PriceAlertsChecker.tsx`) vive enteramente en
`localStorage` del navegador y usa la Notification API para mostrar un aviso
mientras la pestaña está abierta. No hay persistencia en el backend, no hay
service worker, y no se puede avisar con la pestaña cerrada.

No hay cuentas de usuario en el proyecto — cualquier solución debe seguir
funcionando sin login, atada al navegador/dispositivo (igual que hoy).

El backend corre en Render (plan free, `render.yaml`), el frontend en Vercel.
No hay Celery/Redis corriendo (`REDIS_URL` es un placeholder en `settings.py`
sin usar). Se descartó Celery y Render Cron Jobs a favor de **GitHub Actions**
por ser gratuito y no depender del plan de Render.

## Decisión: reemplazo completo

Se reemplaza el sistema de alertas localStorage-only por uno respaldado en el
backend con Web Push real. No conviven ambos sistemas.

## Arquitectura

### Backend (Neon / FastAPI)

**Tabla `push_subscriptions`**
- `id` (UUID, PK)
- `endpoint` (string, único — la URL de push service que da el browser)
- `p256dh_key`, `auth_key` (strings — claves de cifrado de la suscripción)
- `created_at` (timestamptz)

**Tabla `price_alerts`**
- `id` (UUID, PK)
- `subscription_id` (FK -> push_subscriptions, ON DELETE CASCADE)
- `product_id` (FK -> products)
- `target_price` (numeric)
- `created_at` (timestamptz)
- `notified_at_price` (numeric, nullable) — mismo campo que ya usaba el
  localStorage actual (`{productId, targetPrice, createdAt, notifiedAtPrice}`),
  para no re-notificar dos veces al mismo precio.

**Endpoints nuevos** (`app/api/v1/endpoints/push.py`):
- `GET /api/v1/push/vapid-public-key` — devuelve la VAPID public key (no es
  secreta) para que el frontend arme la suscripción sin hardcodearla en el
  bundle.
- `POST /api/v1/push/subscribe` — recibe `{subscription: {endpoint, keys},
  alerts: [{product_id, target_price}]}`. Upsert de la suscripción por
  `endpoint` único, inserta las alertas. Sirve tanto para altas nuevas como
  para la migración en bloque desde localStorage.
- `POST /api/v1/push/alerts` — agrega una alerta a una suscripción ya
  existente (identificada por `endpoint`).
- `DELETE /api/v1/push/alerts/{id}` — borra una alerta puntual.

**Script `backend/scripts/check_price_alerts.py`**
- Corre una vez al día (vía GitHub Actions, no Render).
- Por cada `price_alert` activa, busca el precio actual del producto
  (reusa la misma lógica de "precio actual" que ya existe para
  `CurrentPrice` — no reinventa el cálculo).
- Si `current_price <= target_price` y (`notified_at_price` es NULL o
  distinto del precio actual): manda el push con `pywebpush` usando las
  VAPID keys, y si tiene éxito actualiza `notified_at_price = current_price`.
- Si un producto tiene precio stale (`is_stale`), se saltea esa alerta ese
  día (no notifica con datos viejos).
- Si `pywebpush` devuelve 404/410 (suscripción vencida — el browser la dio
  de baja), borra esa `push_subscription` (cascada borra sus alertas).
- Logging simple a stdout — un run fallido queda visible en la pestaña
  Actions de GitHub, suficiente para un proyecto de una persona.

**`.github/workflows/check-price-alerts.yml`**
- `on: schedule` con cron diario (más `workflow_dispatch` para poder
  correrlo a mano).
- Checkout, setup Python, `pip install -r backend/requirements.txt`,
  `python backend/scripts/check_price_alerts.py`.
- Secrets de GitHub: `DATABASE_URL_UNPOOLED`, `VAPID_PRIVATE_KEY`,
  `VAPID_PUBLIC_KEY`, `VAPID_CLAIMS_EMAIL`.

**VAPID keys:** generadas con `py-vapid` (par de claves EC). La privada solo
vive en GitHub Secrets (la usa el script) — no hace falta en Render, porque
el backend web no manda pushes, solo expone la pública vía endpoint. La
pública también se carga en Vercel como `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (dato
público por diseño del protocolo Web Push, no es un secreto).

### Frontend (Next.js)

**`public/sw.js`** — service worker vanilla, sin `next-pwa`:
- `push` event → `self.registration.showNotification(...)` con el nombre
  del producto y el precio nuevo.
- `notificationclick` event → abre/foca la página del producto
  (`/producto/{id}`).

**`priceAlertsContext.tsx` (reescrito):**
- Al crear una alerta nueva: si no hay `PushSubscription` activa, pide
  permiso de notificación, registra `sw.js`, se suscribe vía
  `PushManager.subscribe()` con la VAPID public key, y manda todo junto a
  `POST /push/subscribe`. Si ya hay suscripción, solo pega a
  `POST /push/alerts`.
- Las alertas ya no se leen de `localStorage` — se listan desde el backend
  (nuevo endpoint de lectura o se devuelven en la respuesta de subscribe/alerts).

**Banner de migración** (nuevo componente, se monta una vez en el layout):
- Si detecta alertas viejas en `localStorage` Y todavía no hay
  `PushSubscription` activa, muestra un banner único: "Activar
  notificaciones push para tus N alertas".
- Un click dispara el mismo flujo de suscripción y manda esas alertas
  (leídas de localStorage) en un solo `POST /push/subscribe`, después
  limpia el localStorage.

**Se elimina:** `PriceAlertsChecker.tsx` (el polling client-side con
Notification API deja de tener sentido — el push llega del backend).

## Manejo de errores

- Suscripción vencida (browser la dio de baja, usuario borró datos): el
  script detecta 404/410 de `pywebpush` y limpia la fila — sin esto, cada
  corrida reintentaría en vano contra una suscripción muerta.
- VAPID keys faltantes en el entorno del workflow: el script falla fuerte
  al arrancar (no silencia el error) — un run rojo en GitHub Actions es la
  única señal de alerta que tiene sentido para un proyecto de una persona.
- Precio stale: se saltea esa alerta en esa corrida, se loguea, se reintenta
  al día siguiente cuando (si) el precio se actualiza.
- Permiso de notificación denegado en el browser: el frontend no fuerza
  nada — si `Notification.permission === 'denied'`, no se ofrece crear
  alertas nuevas hasta que el usuario lo habilite manualmente desde el
  navegador.

## Testing

- Unit tests de la lógica de matching (`check_price_alerts.py`): dado un
  set de alertas y precios actuales fake, cuáles deberían dispararse —
  función pura, mismo patrón que el resto de `tests/`.
- Unit tests de los endpoints nuevos (`push.py`): alta de suscripción,
  upsert por `endpoint` duplicado, alta de alerta, borrado.
- El envío real de push y el flujo de service worker no son testeables por
  unit tests — verificación manual en un browser real una vez desplegado
  (Chrome/Edge en desktop tienen el soporte más simple para probar esto).

## Fuera de alcance (explícitamente no se hace ahora)

- Notificaciones más frecuentes que 1/día (no tiene sentido mientras el
  scraping sea diario).
- Soporte de push en iOS Safari (tiene reglas propias — Web Push ahí
  requiere que la PWA esté "agregada a inicio", fuera del alcance de este
  cambio).
- Panel de administración de suscripciones/alertas.
