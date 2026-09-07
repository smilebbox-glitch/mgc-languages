/* v6.0.4: canonical ownership for practice, games and XP views. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('practice-games')) return;

  const OWNED_VIEWS = Object.freeze(['roleplay', 'games', 'xp']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function featureEnabled(key) {
    const current = state().current();
    const flags = (current.pilot && current.pilot.features) || {};
    return flags[key] !== false;
  }

  function assertFeature(view) {
    const key = view === 'games' ? 'games' : view === 'xp' ? 'xp_economy' : null;
    if (key && !featureEnabled(key)) {
      throw new Error('Эта функция пока не включена для вашей волны пилота');
    }
  }

  function renderer(view) {
    const source = legacy();
    const renderers = {
      roleplay: source.renderPracticeRoleplay,
      games: source.renderPracticeGames,
      xp: source.renderPracticeXP
    };
    const fn = renderers[String(view || '')];
    if (typeof fn !== 'function') throw new Error('Practice renderer is unavailable: ' + view);
    return fn;
  }

  function prepareGo(element) {
    if (!element || !element.dataset || !element.dataset.topic) return;
    const current = state().current();
    current.topic = element.dataset.topic;
    current.scenarioTopic = element.dataset.topic;
    if (element.dataset.go === 'roleplay') {
      current.scenarioIndex = 0;
      current.scenarioAnswered = false;
    }
  }

  async function render(view) {
    const target = String(view || state().get('view') || 'roleplay');
    if (!owns(target)) throw new Error('Practice module does not own view: ' + target);
    assertFeature(target);
    await renderer(target)();
    legacy().ensureChineseStandardBanner();
  }

  async function navigate(view) {
    const target = String(view || 'roleplay');
    if (!owns(target)) return legacy().setView(target);

    state().set('view', target);
    legacy().closeMenu();
    legacy().queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });

    const main = legacy().query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';

    try {
      await render(target);
    } catch (error) {
      if (main) {
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть раздел</h2><p>' +
          legacy().escapeHtml(error && error.message ? error.message : error) +
          '</p><button class="primary" data-go="home">На главную</button></div>';
      }
      throw error;
    }
  }

  function reportError(error) {
    if (frontend.has('error-boundary')) {
      frontend.get('error-boundary').record('practice-navigation', error && error.message ? error.message : error, '', 0, 0);
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
      navigate(button.dataset.view).catch(reportError);
    }, true);

    const main = legacy().query('#main');
    if (main) {
      main.addEventListener('click', function (event) {
        const go = event.target && event.target.closest ? event.target.closest('[data-go]') : null;
        if (!go || !owns(go.dataset.go)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        prepareGo(go);
        navigate(go.dataset.go).catch(reportError);
      }, true);
    }
  }

  frontend.register('practice-games', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
