/* v6.0.0: canonical service-status facade. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('service-status')) return;

  frontend.register('service-status', {
    show: function (message) {
      frontend.get('legacy-app').setServiceStatus(String(message || ''));
    },
    clear: function () {
      frontend.get('legacy-app').setServiceStatus('');
    }
  });
})();
