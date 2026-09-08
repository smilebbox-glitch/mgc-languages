/* v6.0.28: accessibility, focus management and low-overhead UX performance polish. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('ux-performance-v628')) return;

  let installed = false;
  let frame = 0;
  let lastView = '';
  let mainObserver = null;
  let sidebarObserver = null;

  const VIEW_LABELS = Object.freeze({
    home: 'Главная', topics: 'Темы', quiz: 'Тест', roleplay: 'Сценарии',
    course30: 'Курс 30 дней', games: 'Игры', xp: 'XP', exam: 'Итоговый экзамен',
    assistant: 'Помощник', 'chinese-basics': 'Информация о китайском',
    notifications: 'Уведомления', manager: 'Руководитель', admin: 'Админ'
  });

  function state() { return frontend.get('app-state').current(); }
  function query(selector, scope) { return (scope || document).querySelector(selector); }
  function queryAll(selector, scope) { return Array.from((scope || document).querySelectorAll(selector)); }

  function ensureLiveRegion() {
    let node = query('#v628Live');
    if (node) return node;
    node = document.createElement('div');
    node.id = 'v628Live';
    node.className = 'v628-sr-only';
    node.setAttribute('role', 'status');
    node.setAttribute('aria-live', 'polite');
    node.setAttribute('aria-atomic', 'true');
    document.body.appendChild(node);
    return node;
  }

  function currentView() {
    const snapshot = state() || {};
    if (snapshot.view) return String(snapshot.view);
    const active = query('.nav-item.active[data-view]');
    return active ? String(active.dataset.view || '') : '';
  }

  function syncStaticSemantics() {
    const main = query('#main');
    if (main) {
      main.setAttribute('role', 'main');
      if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1');
    }

    const sidebar = query('#sidebar');
    if (sidebar) {
      sidebar.setAttribute('role', 'navigation');
      sidebar.setAttribute('aria-label', 'Основная навигация');
    }

    const menu = query('#menuToggle');
    if (menu && sidebar) {
      menu.setAttribute('aria-controls', 'sidebar');
      menu.setAttribute('aria-expanded', sidebar.classList.contains('open') ? 'true' : 'false');
    }

    const authPanel = query('#authForm');
    if (authPanel) {
      authPanel.id = 'authForm';
      authPanel.setAttribute('role', 'tabpanel');
      authPanel.setAttribute('aria-labelledby', state().authMode === 'register' ? 'authTabRegister' : 'authTabLogin');
    }
    queryAll('.auth-tab').forEach(function (button) {
      const selected = button.classList.contains('active');
      const mode = String(button.dataset.authMode || '');
      button.id = mode === 'register' ? 'authTabRegister' : 'authTabLogin';
      button.setAttribute('role', 'tab');
      button.setAttribute('aria-controls', 'authForm');
      button.setAttribute('aria-selected', selected ? 'true' : 'false');
      button.setAttribute('tabindex', selected ? '0' : '-1');
    });

    queryAll('[data-language]').forEach(function (button) {
      button.setAttribute('aria-pressed', button.classList.contains('active') ? 'true' : 'false');
    });

    queryAll('.nav-item[data-view]').forEach(function (button) {
      if (button.classList.contains('active')) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });

    const pinyin = query('#pinyinToggle');
    if (pinyin && !pinyin.classList.contains('hidden')) {
      pinyin.setAttribute('aria-pressed', pinyin.classList.contains('off') ? 'false' : 'true');
    }

    const toast = query('#toast');
    if (toast) {
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.setAttribute('aria-atomic', 'true');
    }
  }

  function labelRegion(node, label) {
    if (!node) return;
    node.setAttribute('role', 'region');
    if (!node.hasAttribute('aria-label') && !node.hasAttribute('aria-labelledby')) {
      node.setAttribute('aria-label', label);
    }
  }

  function enhanceDynamicContent() {
    const result = query('.game-result-panel');
    if (result) {
      result.setAttribute('role', 'status');
      result.setAttribute('aria-live', 'polite');
      result.setAttribute('aria-atomic', 'true');
    }

    queryAll('.v627-panel').forEach(function (node) {
      labelRegion(node, 'Персональный маршрут следующей тренировки');
      node.classList.add('v628-defer');
    });
    queryAll('.v626-leaderboard').forEach(function (node) {
      labelRegion(node, 'Рейтинг Top-10');
      node.classList.add('v628-defer');
    });
    queryAll('.v624-sim-host').forEach(function (node) {
      labelRegion(node, 'Shift Simulation');
      node.classList.add('v628-defer');
    });
  }

  function announceViewChange() {
    const view = currentView();
    if (!view || view === lastView) return;
    lastView = view;
    const live = ensureLiveRegion();
    live.textContent = 'Открыт раздел: ' + (VIEW_LABELS[view] || view);

    const active = document.activeElement;
    if (active && active.matches && active.matches('input, textarea, select, [contenteditable="true"]')) return;
    const main = query('#main');
    if (!main) return;
    const heading = query('h1, h2, [role="heading"]', main);
    const target = heading || main;
    if (target !== main && !target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
    if (typeof target.focus === 'function') {
      try { target.focus({preventScroll:true}); } catch (_) { target.focus(); }
    }
  }

  function flush() {
    frame = 0;
    syncStaticSemantics();
    enhanceDynamicContent();
    announceViewChange();
  }

  function schedule() {
    if (frame) return;
    if (root.requestAnimationFrame) frame = root.requestAnimationFrame(flush);
    else frame = root.setTimeout(flush, 0);
  }

  function closeMobileMenu() {
    const sidebar = query('#sidebar');
    const backdrop = query('#backdrop');
    const menu = query('#menuToggle');
    if (!sidebar || !sidebar.classList.contains('open')) return false;
    sidebar.classList.remove('open');
    if (backdrop) backdrop.classList.add('hidden');
    if (menu) {
      menu.setAttribute('aria-expanded', 'false');
      if (typeof menu.focus === 'function') menu.focus();
    }
    return true;
  }

  function onKeyDown(event) {
    if (event.key === 'Escape' && closeMobileMenu()) {
      event.preventDefault();
      return;
    }
    if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) return;
    const active = document.activeElement;
    if (active && active.matches && active.matches('input, textarea, select, [contenteditable="true"]')) return;
    const search = query('#pilotSearch');
    if (!search || search.offsetParent === null) return;
    event.preventDefault();
    search.focus();
    if (typeof search.select === 'function') search.select();
  }

  function onAuthTabKeyDown(event) {
    const target = event.target && event.target.closest ? event.target.closest('.auth-tab') : null;
    if (!target || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    const tabs = queryAll('.auth-tab:not(.hidden)');
    if (tabs.length < 2) return;
    const index = tabs.indexOf(target);
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const next = tabs[(index + delta + tabs.length) % tabs.length];
    event.preventDefault();
    next.click();
    next.focus();
    schedule();
  }

  function install() {
    if (installed) return;
    installed = true;
    ensureLiveRegion();
    document.addEventListener('keydown', onKeyDown);
    const authTabs = query('#authTabs');
    if (authTabs) authTabs.addEventListener('keydown', onAuthTabKeyDown);
    document.addEventListener('click', schedule, true);
    document.addEventListener('mgc:state-change', schedule);
    document.addEventListener('mgc:frontend-ready', schedule);

    const main = query('#main');
    if (main && root.MutationObserver) {
      mainObserver = new MutationObserver(schedule);
      mainObserver.observe(main, {childList:true, subtree:true});
    }
    const sidebar = query('#sidebar');
    if (sidebar && root.MutationObserver) {
      sidebarObserver = new MutationObserver(schedule);
      sidebarObserver.observe(sidebar, {attributes:true, attributeFilter:['class'], subtree:false});
    }
    schedule();
  }

  frontend.register('ux-performance-v628', {
    install: install,
    schedule: schedule,
    syncStaticSemantics: syncStaticSemantics,
    enhanceDynamicContent: enhanceDynamicContent,
    closeMobileMenu: closeMobileMenu
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
