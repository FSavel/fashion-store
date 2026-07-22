const CACHE_NAME = 'loja-moda-v2';

// Ficheiros estáticos essenciais para funcionamento offline
const ASSETS_TO_CACHE = [
  '/',
  '/cart',
  '/sobre',
  '/static/css/style.css',
  '/static/js/app.js',
  '/manifest.json',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

// ==========================================
// 1. INSTALAÇÃO (Pre-caching dos recursos)
// ==========================================
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Adiciona ficheiros um a um para evitar falha total caso um falhe
      return Promise.allSettled(
        ASSETS_TO_CACHE.map((asset) => cache.add(asset))
      );
    })
  );
  self.skipWaiting();
});

// ==========================================
// 2. ATIVAÇÃO (Limpeza de caches antigas)
// ==========================================
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// ==========================================
// 3. INTERCEÇÃO DE PEDIDOS (Estratégia Network First com Fallback)
// ==========================================
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Ignora requisições que NÃO sejam GET (ex: POST no checkout)
  if (event.request.method !== 'GET') {
    return;
  }

  // Ignora rotas administrativas e uploads dinâmicos (Cloudinary) da cache do SW
  if (url.pathname.startsWith('/admin') || url.hostname.includes('cloudinary.com')) {
    return;
  }

  // ESTRATÉGIA PARA APIS: Tenta sempre a rede primeiro, sem guardar cache pesada de APIs
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(event.request))
    );
    return;
  }

  // ESTRATÉGIA GERAL: Network First -> Fallback para Cache
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Se a resposta for válida (status 200), guarda uma cópia na cache
        if (response && response.status === 200 && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // Se estiver offline ou a rede falhar, entrega o que está na cache
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Caso seja navegação de página e esteja offline, entrega a home
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
        });
      })
  );
});
