/* v6.0.29 hotfix: canonical CSRF-aware API client with bounded fetch time. */
(function () {
  'use strict';
  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('api-client')) return;

  const DEFAULT_TIMEOUT_MS = 12000;

  function cookieValue(name) {
    const prefix = String(name) + '=';
    const row = document.cookie.split(';').map(function (value) { return value.trim(); })
      .find(function (value) { return value.startsWith(prefix); });
    return row ? decodeURIComponent(row.slice(prefix.length)) : '';
  }

  async function request(url, options) {
    const opts = Object.assign({credentials: 'same-origin'}, options || {});
    const timeoutMs = Math.max(0, Number(opts.timeoutMs == null ? DEFAULT_TIMEOUT_MS : opts.timeoutMs));
    delete opts.timeoutMs;

    opts.headers = Object.assign({}, opts.headers || {});
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers = Object.assign({'Content-Type': 'application/json'}, opts.headers || {});
    }
    const method = String(opts.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrf = cookieValue('mgc_csrf');
      if (csrf) opts.headers['X-CSRF-Token'] = csrf;
    }

    let timer = null;
    let controller = null;
    if (!opts.signal && timeoutMs > 0 && typeof AbortController === 'function') {
      controller = new AbortController();
      opts.signal = controller.signal;
      timer = window.setTimeout(function () { controller.abort(); }, timeoutMs);
    }

    let response;
    try {
      response = await fetch(url, opts);
    } catch (error) {
      if (error && error.name === 'AbortError') {
        throw new Error('Сервер не ответил вовремя. Повторите действие.');
      }
      throw error;
    } finally {
      if (timer) window.clearTimeout(timer);
    }

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
    cookieValue: cookieValue,
    defaultTimeoutMs: DEFAULT_TIMEOUT_MS
  });
})();