/* v6.0.33 — UI policy and navigation hardening for the canonical visual reset. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) return;

  const GUARDED_VIEWS = new Set(['exam', 'assistant', 'chinese-basics']);
  const REMOVED_GAME = 'match';
  let installed = false;

  function legacy() {
    return frontend.has('legacy-app') ? frontend.get('legacy-app') : null;
  }

  function state() {
    return frontend.has('app-state') ? frontend.get('app-state') : null;
  }

  function report(scope, error) {
    try {
      if (!frontend.has('error-boundary')) return;
      frontend.get('error-boundary').record(
        String(scope || 'v633-ui'),
        error && error.message ? error.message : String(error || 'unknown error'),
        '', 0, 0
      );
    } catch (_) {}
  }

  function escapeHtml(value) {
    const app = legacy();
    if (app && typeof app.escapeHtml === 'function') return app.escapeHtml(value);
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch];
    });
  }

  function clearRemovedGameSession() {
    const store = state();
    if (!store) return;
    try {
      const snapshot = store.current() || {};
      const active = snapshot.gameSessionV618;
      const legacySession = snapshot.gameSession;
      if (active && String(active.game_type || active.type || '') === REMOVED_GAME) {
        store.patch({gameSessionV618:null, gameAnswersV618:[], gameIndexV618:0, gameSelectionV618:[]});
      }
      if (legacySession && String(legacySession.game_type || legacySession.type || '') === REMOVED_GAME) {
        store.patch({gameSession:null, gameAnswers:[], gameIndex:0, phraseSelected:[]});
      }
    } catch (error) {
      report('clear-removed-game', error);
    }
  }

  function removeRejectedGameFromCatalog(scope) {
    const node = scope && scope.querySelectorAll ? scope : document;
    node.querySelectorAll('[data-start-v618-game="match"],[data-start-game="match"],[data-game-type="match"]').forEach(function (button) {
      const card = button.closest('.game-lab-card,.game-card,.arcade-card') || button;
      card.remove();
    });

    const main = document.getElementById('main');
    if (!main) return;
    main.querySelectorAll('.game-lab-summary b,.game-lab-head .kicker,.page-head .kicker').forEach(function (el) {
      const text = String(el.textContent || '').trim();
      if (text === '20') el.textContent = '19';
      if (/20\s*ИГР/i.test(text)) el.textContent = text.replace(/20\s*ИГР/i, '19 ИГР');
    });
  }

  function navigationError(view, error) {
    const main = document.getElementById('main');
    if (!main) return;
    const labels = {
      exam:'Итоговый экзамен',
      assistant:'Помощник',
      'chinese-basics':'Информация о китайском'
    };
    const label = labels[view] || 'Раздел';
    main.innerHTML = '<section class="card v633-route-error"><div class="kicker">MGC LANGUAGE LAB</div>' +
      '<h2>' + escapeHtml(label) + '</h2><p>Раздел временно не открылся. Повторите загрузку.</p>' +
      '<button class="primary" data-v633-retry="' + escapeHtml(view) + '">Повторить</button></section>';
    const retry = main.querySelector('[data-v633-retry]');
    if (retry) retry.addEventListener('click', function () { openView(view); });
    report('navigation-' + view, error);
  }

  function openView(view) {
    const target = String(view || 'home');
    try {
      if (!frontend.has('navigation')) throw new Error('Navigation module unavailable');
      Promise.resolve(frontend.get('navigation').setView(target)).catch(function (error) {
        navigationError(target, error);
      });
    } catch (error) {
      navigationError(target, error);
    }
  }

  function installGuardedNavigation() {
    /* Window capture runs before legacy document capture handlers and prevents
       competing modules from swallowing these three critical sidebar routes. */
    root.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
      if (!button || !button.closest('.sidebar,.topbar')) return;
      const view = String(button.dataset.view || '');
      if (!GUARDED_VIEWS.has(view)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      openView(view);
    }, true);
  }

  function enforceHomeHierarchy() {
    const main = document.getElementById('main');
    if (!main) return;
    const dashboard = main.querySelector('.pilot-dashboard');
    if (!dashboard) return;
    dashboard.setAttribute('data-v633-home', 'canonical');

    const nextTitle = dashboard.querySelector('.pilot-next-head h2');
    if (nextTitle) nextTitle.textContent = 'Сегодня';
    const nextSubtitle = dashboard.querySelector('.pilot-next-head p');
    if (nextSubtitle) nextSubtitle.textContent = 'Короткая практика: термины, рабочая ситуация и мини-тест.';

    const topicsTitle = dashboard.querySelector('.pilot-topics .pilot-section-head h2');
    if (topicsTitle) topicsTitle.textContent = 'Темы для работы в автопроме';
  }

  function rescueDom() {
    clearRemovedGameSession();
    removeRejectedGameFromCatalog(document);
    enforceHomeHierarchy();

    const main = document.getElementById('main');
    if (main && /Соберите\s+пару/i.test(String(main.textContent || ''))) {
      clearRemovedGameSession();
      openView('games');
    }
  }

  function install() {
    if (installed) return;
    installed = true;
    installGuardedNavigation();
    rescueDom();

    const observer = new MutationObserver(function (records) {
      let changed = false;
      records.forEach(function (record) {
        if (record.addedNodes && record.addedNodes.length) changed = true;
      });
      if (changed) rescueDom();
    });
    observer.observe(document.documentElement, {childList:true, subtree:true});

    document.addEventListener('mgc:frontend-ready', rescueDom);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
