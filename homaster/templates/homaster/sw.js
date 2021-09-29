// Service Worker インストール時に実行される
self.addEventListener('install', (event) => {
  console.log('service worker install ...');
});

// Service Worker アクティベート時に実行される
self.addEventListener('activate', (event) => {
  console.info('activate');
  // console.info('activate', event);
});

self.addEventListener('push', function(event) {
  // console.log('[Service Worker] Push Received.');
  // console.log(`[Service Worker] Push had this data: "${event.data.text()}"`);

  const eventInfo = event.data.text();
  const data = JSON.parse(eventInfo);
  const head = data.head;
  const body = data.body;

  // Keep the service worker alive until the notification is created.
  event.waitUntil(
      self.registration.showNotification(head, {
          body: body,
          // icon: 'https://i.imgur.com/MZM3K5w.png'
      })
  );
});
