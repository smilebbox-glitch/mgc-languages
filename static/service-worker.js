/* MGC Language Lab PWA shell — v6.0.31 mobile/web experience.
 * Security invariant: only immutable/public static assets may enter Cache Storage.
 * Authentication, API, manager/admin and navigation responses are always network-only.
 */
'use strict';

const STATIC_CACHE = 'mgc-language-static-v631-mobile';
const OFFLINE_URL = '/offline.html';
const PRECACHE = [
  OFFLINE_URL,
  '/manifest.webmanifest',
  '/icons/app-icon.svg',
  '/icons/app-icon-maskable.svg',
  '/mobile_experience_v631.css',
  '/frontend/mobile_experience_v631.js'
];

const SENSITIVE_PREFIXES = [
  '/api',
  '/auth',
  '/admin',
  '/manager',
  '/observability',
  '/notifications',
  '/user',
  '/users',
  '/metrics',
  '/health',
  '/ready'
];

const STATIC_ASSET_RE = /\.(?:css|js|mjs|svg|png|jpe?g|webp|gif|ico|woff2?|ttf)$/i;

function isSensitivePath(pathname) {
  return SENSITIVE_PREFIXES.some(function (prefix) {
    return pathname === prefix || pathname.startsWith(prefix + '/');
  });
}

function hasSensitiveRequestHeaders(request) {
  return request.headers.has('authorization') ||
    request.headers.has('cookie') ||
    request.headers.has('range');
}

function isCacheableStaticRequest(request, url) {
  if (request.method !== 'GET') return false;
  if (url.origin !== self.location.origin) return false;
  if (isSensitivePath(url.pathname)) return false;
  if (hasSensitiveRequestHeaders(request)) return false;
  return STATIC_ASSET_RE.test(url.pathname);
}

function isCacheableStaticResponse(response) {
  if (!response || !response.ok || response.type !== 'basic') return false;
  const cacheControl = (response.headers.get('cache-control') || '').toLowerCase();
  if (cacheControl.includes('no-store') || cacheControl.includes('private')) return false;
  if (response.headers.has('set-cookie')) return false;
  return true;
}

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(function (cache) { return cache.addAll(PRECACHE); })
      .then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (key) {
          if (key.startsWith('mgc-language-') && key !== STATIC_CACHE) {
            return caches.delete(key);
          }
          return Promise.resolve(false);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (event) {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Sensitive endpoints and credential/range-shaped requests are never intercepted,
  // cached or replaced with offline data.
  if (isSensitivePath(url.pathname) || hasSensitiveRequestHeaders(request)) return;

  // HTML/navigation can contain authentication state. Always go to the server.
  // Only a generic, non-user-specific page is available when the network is down.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request, {cache: 'no-store'})
        .catch(function () { return caches.match(OFFLINE_URL); })
    );
    return;
  }

  if (!isCacheableStaticRequest(request, url)) return;

  event.respondWith(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.match(request).then(function (cached) {
        const refreshed = fetch(request, {cache: 'no-store'}).then(function (response) {
          if (isCacheableStaticResponse(response)) {
            cache.put(request, response.clone()).catch(function () {});
          }
          return response;
        });
        return cached || refreshed;
      });
    })
  );
});
