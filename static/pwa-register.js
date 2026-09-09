(function () {
  'use strict';

  const isLocalhost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
  const isSecureContextForPwa = window.location.protocol === 'https:' || isLocalhost;

  function emit(name, detail) {
    document.dispatchEvent(new CustomEvent(name, {detail: detail || {}}));
  }

  const standalone = !!(
    (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) ||
    window.navigator.standalone === true
  );
  if (standalone) document.documentElement.classList.add('pwa-standalone');

  if (!('serviceWorker' in navigator)) {
    emit('mgc:pwa-status', {supported: false, reason: 'service-worker-unsupported', standalone: standalone});
    return;
  }

  if (!isSecureContextForPwa) {
    emit('mgc:pwa-status', {supported: true, active: false, reason: 'secure-context-required', standalone: standalone});
    return;
  }

  let controllerSeen = !!navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener('controllerchange', function () {
    if (controllerSeen) emit('mgc:pwa-update', {ready: true});
    controllerSeen = true;
  });

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
      updateViaCache: 'none'
    }).then(function (registration) {
      emit('mgc:pwa-status', {
        supported: true,
        active: true,
        scope: registration.scope,
        standalone: standalone
      });

      registration.addEventListener('updatefound', function () {
        const worker = registration.installing;
        if (!worker) return;
        worker.addEventListener('statechange', function () {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            emit('mgc:pwa-update', {ready: true, scope: registration.scope});
          }
        });
      });

      registration.update().catch(function () {});
    }).catch(function (error) {
      emit('mgc:pwa-status', {
        supported: true,
        active: false,
        reason: 'registration-failed',
        standalone: standalone,
        message: String(error && error.message ? error.message : error)
      });
    });
  });
})();
