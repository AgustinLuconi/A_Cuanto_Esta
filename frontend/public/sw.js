// Service worker mínimo para Web Push -- no cachea nada (no es un PWA
// offline-first), solo reacciona a 'push' (mostrar la notificación) y
// 'notificationclick' (abrir/enfocar la página del producto).

self.addEventListener("push", (event) => {
  // Chrome/Firefox pueden revocar el permiso de notificaciones si un SW
  // recibe un evento 'push' y no muestra ninguna notificación ("silent
  // push" policy) -- por eso, aunque el payload venga vacío o corrupto,
  // siempre se muestra algo en vez de salir sin hacer nada.
  let payload = {};
  if (event.data) {
    try {
      payload = event.data.json();
    } catch {
      payload = {};
    }
  }
  const { title, product_id, price, target_price } = payload;
  const body = price != null && target_price != null
    ? `Ahora $${price} (tu objetivo: $${target_price})`
    : "Revisá tus alertas de precio.";
  event.waitUntil(
    self.registration.showNotification(title || "¡Bajó de precio!", {
      body,
      tag: product_id ? `price-alert-${product_id}` : "price-alert",
      data: { productId: product_id },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const productId = event.notification.data && event.notification.data.productId;
  const url = productId ? `/producto/${productId}` : "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.indexOf(url) !== -1 && "focus" in client) return client.focus();
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
