/* v6.0.32 — navigation and visual-regression rescue for MGC Language Lab. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) return;

  const SIDEBAR_VIEWS = new Set([
    'home','topics','quiz','roleplay','course30','games','xp','exam',
    'assistant','chinese-basics','notifications','manager','admin'
  ]);

  function report(scope, error) {
    try {
      if (frontend.has('error-boundary')) {
        frontend.get('error-boundary').record(
          String(scope || 'v632-rescue'),
          error && error.message ? error.message : String(error || 'unknown error'),
          '', 0, 0
        );
      }
    } catch (_) {}
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (ch) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch];
    });
  }

  function showNavigationError(view, error) {
    const main = document.getElementById('main');
    if (!main) return;
    const labels = {
      exam:'Итоговый экзамен',
      assistant:'Помощник',
      'chinese-basics':'Информация о китайском'
    };
    const label = labels[view] || 'Раздел';
    main.innerHTML = '<div class="card v632-route-error"><div class="kicker">MGC LANGUAGE LAB</div>' +
      '<h2>' + escapeHtml(label) + '</h2><p>Раздел не открылся корректно. Интерфейс восстановлен, но модуль вернул ошибку.</p>' +
      '<button class="primary" data-v632-retry="' + escapeHtml(view) + '">Повторить</button></div>';
    const retry = main.querySelector('[data-v632-retry]');
    if (retry) retry.addEventListener('click', function () { navigate(view); });
    report('route-' + view, error);
  }

  function clearRemovedMatchSession() {
    try {
      if (!frontend.has('app-state')) return;
      const state = frontend.get('app-state');
      const snapshot = state.current() || {};
      const session = snapshot.gameSessionV618;
      if (session && String(session.game_type || session.type || '') === 'match') {
        state.patch({
          gameSessionV618:null,
          gameAnswersV618:[],
          gameIndexV618:0,
          gameSelectionV618:[]
        });
      }
      const legacySession = snapshot.gameSession;
      if (legacySession && String(legacySession.game_type || legacySession.type || '') === 'match') {
        state.patch({gameSession:null, gameAnswers:[], gameIndex:0, phraseSelected:[]});
      }
    } catch (error) {
      report('clear-match-session', error);
    }
  }

  function navigate(view) {
    const target = String(view || 'home');
    if (target === 'games') clearRemovedMatchSession();
    try {
      if (!frontend.has('navigation')) throw new Error('Navigation module is unavailable');
      Promise.resolve(frontend.get('navigation').setView(target)).catch(function (error) {
        showNavigationError(target, error);
      });
    } catch (error) {
      showNavigationError(target, error);
    }
  }

  /*
   * Several legacy modules register document-level capture handlers and call
   * stopImmediatePropagation(). A single window-level router runs earlier in the
   * event path, so sidebar/topbar navigation remains deterministic.
   */
  root.addEventListener('click', function (event) {
    const target = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
    if (!target) return;
    const inChrome = target.closest('.sidebar,.topbar');
    if (!inChrome) return;
    const view = String(target.dataset.view || '');
    if (!SIDEBAR_VIEWS.has(view)) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    navigate(view);
  }, true);

  function removeMatchLaunchers(scope) {
    const rootNode = scope && scope.querySelectorAll ? scope : document;
    rootNode.querySelectorAll('[data-start-v618-game="match"],[data-start-game="match"],[data-game-type="match"]').forEach(function (node) {
      const card = node.closest('.game-lab-card,.game-card,.arcade-card') || node;
      card.remove();
    });

    rootNode.querySelectorAll('.game-filter-row,.game-lab-summary,.game-lab-head,.page-head').forEach(function (node) {
      node.querySelectorAll('*').forEach(function (el) {
        if (el.children.length) return;
        const text = String(el.textContent || '').trim();
        if (text === '20') el.textContent = '19';
        else if (/20\s+ИГР/i.test(text)) el.textContent = text.replace(/20\s+ИГР/i, '19 ИГР');
        else if (/20\s+разных\s+механик/i.test(text)) el.textContent = text.replace(/20/i, '19');
      });
    });
  }

  function rescueCurrentDom() {
    clearRemovedMatchSession();
    removeMatchLaunchers(document);

    const main = document.getElementById('main');
    if (main && /Соберите\s+пару/i.test(main.textContent || '')) {
      clearRemovedMatchSession();
      navigate('games');
    }
  }

  const observer = new MutationObserver(function (records) {
    let shouldRescue = false;
    records.forEach(function (record) {
      if (record.addedNodes && record.addedNodes.length) shouldRescue = true;
    });
    if (shouldRescue) removeMatchLaunchers(document);
  });

  function install() {
    rescueCurrentDom();
    observer.observe(document.documentElement, {childList:true, subtree:true});

    document.addEventListener('mgc:frontend-ready', function () {
      rescueCurrentDom();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
