// Service worker mínimo para Web Push -- no cachea nada (no es un PWA
// offline-first), solo reacciona a 'push' (mostrar la notificación) y
// 'notificationclick' (abrir/enfocar la página del producto).

self.addEventListener("push", (event) => {
  if (!event.data) return;
  let payload;
  try {
    payload = event.data.json();
  } catch {
    return;
  }
  const { title, product_id, price, target_price } = payload;
  event.waitUntil(
    self.registration.showNotification(title || "¡Bajó de precio!", {
      body: `Ahora $${price} (tu objetivo: $${target_price})`,
      tag: `price-alert-${product_id}`,
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
