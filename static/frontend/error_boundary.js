/* v6.0.2: privacy-safe frontend error boundary and local diagnostics. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('error-boundary')) return;

  const MAX_EVENTS = 20;
  const events = [];
  let statusShown = false;

  function scrub(value) {
    let text = String(value == null ? '' : value);
    text = text.replace(/(authorization\s*:\s*bearer\s+)[^\s]+/ig, '$1[redacted]');
    text = text.replace(/(mgc_(?:session|csrf)=)[^;\s]+/ig, '$1[redacted]');
    text = text.replace(/((?:password|token|secret)=)[^&\s]+/ig, '$1[redacted]');
    return text.slice(0, 500);
  }

  function safeSource(value) {
    const raw = String(value || '');
    if (!raw) return '';
    try {
      const parsed = new URL(raw, window.location.href);
      return parsed.pathname.slice(-180);
    } catch (_) {
      return scrub(raw.split('?')[0].split('#')[0]).slice(-180);
    }
  }

  function markDegraded() {
    if (document && document.documentElement) {
      document.documentElement.dataset.mgcFrontend = 'degraded';
    }
    if (!statusShown && frontend.has('service-status')) {
      statusShown = true;
      frontend.get('service-status').show(
        'Интерфейс столкнулся с ошибкой. Повторите действие; если проблема останется, обновите страницу.'
      );
    }
  }

  function record(type, message, source, line, column) {
    const item = Object.freeze({
      at: new Date().toISOString(),
      type: scrub(type || 'error'),
      message: scrub(message || 'Неизвестная ошибка'),
      source: safeSource(source),
      line: Number(line || 0),
      column: Number(column || 0)
    });
    events.push(item);
    while (events.length > MAX_EVENTS) events.shift();
    markDegraded();
    return item;
  }

  function snapshot() {
    return events.map(function (item) { return Object.assign({}, item); });
  }

  function clear() {
    events.splice(0, events.length);
    statusShown = false;
    if (document && document.documentElement && frontend.diagnostics.ready) {
      document.documentElement.dataset.mgcFrontend = 'ready';
    }
  }

  window.addEventListener('error', function (event) {
    record('error', event.message, event.filename, event.lineno, event.colno);
  });

  window.addEventListener('unhandledrejection', function (event) {
    const reason = event.reason instanceof Error ? event.reason.message : event.reason;
    record('unhandledrejection', reason, '', 0, 0);
  });

  frontend.register('error-boundary', {
    record: record,
    snapshot: snapshot,
    clear: clear,
    maxEvents: MAX_EVENTS
  });
})();
