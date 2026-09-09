(function () {
  'use strict';

  const isLocalhost = ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
  const isSecureContextForPwa = window.location.protocol === 'https:' || isLocalhost;

  function emit(name, detail) {
    document.dispatchEvent(new CustomEvent(name, {detail: detail || {}}));
  }

  if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
    document.documentElement.classList.add('pwa-standalone');
  }

  if (!('serviceWorker' in navigator)) {
    emit('mgc:pwa-status', {supported: false, reason: 'service-worker-unsupported'});
    return;
  }

  if (!isSecureContextForPwa) {
    emit('mgc:pwa-status', {supported: true, active: false, reason: 'secure-context-required'});
    return;
  }

  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
      updateViaCache: 'none'
    }).then(function (registration) {
      emit('mgc:pwa-status', {
        supported: true,
        active: true,
        scope: registration.scope
      });

      // Check for service-worker updates without relying on an HTTP cache.
      registration.update().catch(function () {});
    }).catch(function (error) {
      emit('mgc:pwa-status', {
        supported: true,
        active: false,
        reason: 'registration-failed',
        message: String(error && error.message ? error.message : error)
      });
    });
  });
})();
