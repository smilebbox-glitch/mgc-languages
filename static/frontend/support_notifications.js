/* v6.0.5: canonical ownership for user support signals and notifications. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('support-notifications')) return;

  const OWNED_VIEWS = Object.freeze(['notifications']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function featureEnabled() {
    const current = state().current();
    const flags = (current.pilot && current.pilot.features) || {};
    return flags.learning_nudges !== false;
  }

  function assertFeature() {
    if (!featureEnabled()) {
      throw new Error('Эта функция пока не включена для вашей волны пилота');
    }
  }

  function pageHead(kicker, title, subtitle) {
    const esc = legacy().escapeHtml;
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function toast(message) {
    legacy().toast(String(message || ''));
  }

  function showStatus(message) {
    frontend.get('service-status').show(String(message || ''));
  }

  function clearStatus() {
    frontend.get('service-status').clear();
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'support-notifications'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  async function loadNotificationState() {
    const values = await Promise.all([
      api().request('/api/notifications/settings'),
      api().request('/api/notifications/pending')
    ]);
    const settings = values[0] || {};
    const nudges = (values[1] && values[1].items) || [];
    state().patch({notificationSettings: settings, nudges: nudges});
    return {settings: settings, nudges: nudges};
  }

  function settingsPayload() {
    const query = legacy().query;
    return {
      mode: query('#nudgeMode').value,
      window_start: query('#nudgeStart').value,
      window_end: query('#nudgeEnd').value,
      browser_enabled: query('#browserNudges').checked
    };
  }

  async function saveSettings() {
    try {
      await api().request('/api/notifications/settings', {
        method: 'PUT',
        body: JSON.stringify(settingsPayload())
      });
      toast('Настройки сохранены');
      await render();
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('notification-settings', error);
    }
  }

  async function markRead(id) {
    try {
      await api().request('/api/notifications/' + encodeURIComponent(String(id)) + '/read', {method: 'POST'});
      await render();
    } catch (error) {
      toast(error && error.message ? error.message : error);
      reportError('notification-read', error);
    }
  }

  async function requestBrowserPermission() {
    if (!('Notification' in root)) {
      toast('Браузер не поддерживает Notifications API');
      return 'unsupported';
    }
    try {
      const permission = await root.Notification.requestPermission();
      toast(permission === 'granted' ? 'Разрешено' : 'Не разрешено');
      const checkbox = legacy().query('#browserNudges');
      if (permission === 'granted' && checkbox) checkbox.checked = true;
      return permission;
    } catch (error) {
      reportError('notification-permission', error);
      toast('Не удалось запросить разрешение на уведомления');
      return 'error';
    }
  }

  function maybeBrowserNudge() {
    if (!featureEnabled()) return false;
    const current = state().current();
    const nudges = current.nudges || [];
    const settings = current.notificationSettings;
    if (!nudges.length || !settings || !settings.browser_enabled) return false;
    if (!('Notification' in root) || root.Notification.permission !== 'granted') return false;
    const item = nudges[0];
    try {
      new root.Notification(item.title, {body: item.body, tag: 'mgc-learning-nudge'});
      return true;
    } catch (error) {
      reportError('notification-browser', error);
      return false;
    }
  }

  function bindViewActions() {
    const query = legacy().query;
    const queryAll = legacy().queryAll;
    const save = query('#saveNudges');
    if (save) save.addEventListener('click', function () { void saveSettings(); });
    const enable = query('#enableBrowser');
    if (enable) enable.addEventListener('click', function () { void requestBrowserPermission(); });
    queryAll('[data-read-nudge]').forEach(function (button) {
      button.addEventListener('click', function () { void markRead(button.dataset.readNudge); });
    });
  }

  async function render() {
    assertFeature();
    const data = await loadNotificationState();
    const settings = data.settings || {};
    const nudges = data.nudges || [];
    const esc = legacy().escapeHtml;
    const main = legacy().query('#main');
    if (!main) throw new Error('Notifications view missing #main');

    main.innerHTML = pageHead(
      'Learning Nudge Engine',
      'Напоминания без давления',
      'Сервис пишет редко, только когда есть смысл продолжить. После трёх проигнорированных напоминаний он замолкает до вашего возвращения.'
    ) +
      '<div class="grid two"><section class="card"><h3>Частота</h3><label>Режим<select id="nudgeMode">' +
      '<option value="off">Выключены</option><option value="minimal">Минимальные · примерно раз в неделю</option>' +
      '<option value="normal">Обычные · по необходимости раз в 2–4 дня</option><option value="active">Активные · можно ежедневно</option>' +
      '</select></label><div class="grid two compact-grid"><label>Не раньше<input id="nudgeStart" type="time" value="' +
      esc(settings.window_start || '') + '"></label><label>Не позже<input id="nudgeEnd" type="time" value="' +
      esc(settings.window_end || '') + '"></label></div><label class="toggle-line"><input id="browserNudges" type="checkbox" ' +
      (settings.browser_enabled ? 'checked' : '') + '> Показывать браузерное уведомление, когда сервис открыт</label>' +
      '<button id="saveNudges" class="primary">Сохранить</button><button id="enableBrowser" class="ghost">Разрешить уведомления браузера</button></section>' +
      '<section class="card"><h3>Последние</h3>' +
      (nudges.length ? nudges.map(function (item) {
        return '<div class="nudge-history"><b>' + esc(item.title) + '</b><p>' + esc(item.body) +
          '</p><button class="ghost small-button" data-read-nudge="' + esc(item.id) + '">Прочитано</button></div>';
      }).join('') : '<p class="muted">Сейчас ничего не требует внимания.</p>') +
      '</section></div>';

    const mode = legacy().query('#nudgeMode');
    if (mode) mode.value = settings.mode || 'normal';
    bindViewActions();
  }

  async function navigate(view) {
    const target = String(view || 'notifications');
    if (!owns(target)) return legacy().setView(target);
    assertFeature();

    state().set('view', target);
    legacy().closeMenu();
    legacy().queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });

    const main = legacy().query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';

    try {
      await render();
    } catch (error) {
      if (main) {
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' +
          legacy().escapeHtml(error && error.message ? error.message : error) +
          '</p><button class="primary" data-go="home">На главную</button></div>';
      }
      throw error;
    }
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
      if (!button || !owns(button.dataset.view)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate(button.dataset.view).catch(function (error) {
        reportError('support-notifications-navigation', error);
      });
    }, true);
  }

  frontend.register('support-notifications', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    load: loadNotificationState,
    saveSettings: saveSettings,
    markRead: markRead,
    requestBrowserPermission: requestBrowserPermission,
    maybeBrowserNudge: maybeBrowserNudge,
    toast: toast,
    showStatus: showStatus,
    clearStatus: clearStatus,
    reportError: reportError,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
