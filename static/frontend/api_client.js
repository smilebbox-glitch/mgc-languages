/* v6.0.0: canonical CSRF-aware API client for modular frontend code. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('api-client')) return;

  function cookieValue(name) {
    const prefix = String(name) + '=';
    const row = document.cookie.split(';').map(function (value) { return value.trim(); })
      .find(function (value) { return value.startsWith(prefix); });
    return row ? decodeURIComponent(row.slice(prefix.length)) : '';
  }

  async function request(url, options) {
    const opts = Object.assign({credentials: 'same-origin'}, options || {});
    opts.headers = Object.assign({}, opts.headers || {});
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers || {});
    }
    const method = String(opts.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrf = cookieValue('mgc_csrf');
      if (csrf) opts.headers['X-CSRF-Token'] = csrf;
    }

    const response = await fetch(url, opts);
    let data = {};
    try { data = await response.json(); } catch (_) {}

    if (response.status === 401 && !String(url).includes('/api/login')) {
      if (frontend.has('navigation')) frontend.get('navigation').showAuth();
      throw new Error('Требуется повторный вход');
    }
    if (!response.ok) {
      if (response.status === 503 && data.code === 'database_unavailable') {
        frontend.get('service-status').show(
          'Сервис временно недоступен из-за базы данных. Интерфейс остаётся открыт; повторите действие через несколько секунд.'
        );
      }
      throw new Error(data.detail || 'Не удалось выполнить запрос');
    }
    if (!String(url).includes('/api/pronunciation/')) frontend.get('service-status').clear();
    return data;
  }

  frontend.register('api-client', {
    request: request,
    cookieValue: cookieValue
  });
})();
