/* v6.0.3: canonical ownership for core learning views. */
(function () {
  'use strict';

  const frontend = window.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('learning')) return;

  const OWNED_VIEWS = Object.freeze(['home', 'topics', 'quiz', 'course30']);
  const owned = new Set(OWNED_VIEWS);
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function renderer(view) {
    const source = legacy();
    const renderers = {
      home: source.renderLearningHome,
      topics: source.renderLearningTopics,
      quiz: source.renderLearningQuiz,
      course30: source.renderLearningCourse30
    };
    const fn = renderers[String(view || '')];
    if (typeof fn !== 'function') throw new Error('Learning renderer is unavailable: ' + view);
    return fn;
  }

  function selectTopicFromElement(element) {
    if (!element || !element.dataset || !element.dataset.topic) return;
    const current = state().current();
    current.topic = element.dataset.topic;
    current.scenarioTopic = element.dataset.topic;
    if (element.dataset.go === 'quiz') {
      current.quiz = null;
      current.quizIndex = 0;
      current.quizScore = 0;
      current.quizAnswered = false;
    }
  }

  async function render(view) {
    const target = String(view || state().get('view') || 'home');
    if (!owns(target)) throw new Error('Learning module does not own view: ' + target);
    await renderer(target)();
    legacy().ensureChineseStandardBanner();
  }

  async function navigate(view) {
    const target = String(view || 'home');
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

  function install() {
    if (installed) return;
    installed = true;

    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
      if (!button || !owns(button.dataset.view)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate(button.dataset.view).catch(function (error) {
        if (frontend.has('error-boundary')) frontend.get('error-boundary').record('learning-navigation', error.message || error, '', 0, 0);
      });
    }, true);

    const main = legacy().query('#main');
    if (main) {
      main.addEventListener('click', function (event) {
        const go = event.target && event.target.closest ? event.target.closest('[data-go]') : null;
        if (!go || !owns(go.dataset.go)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        selectTopicFromElement(go);
        navigate(go.dataset.go).catch(function (error) {
          if (frontend.has('error-boundary')) frontend.get('error-boundary').record('learning-navigation', error.message || error, '', 0, 0);
        });
      }, true);
    }
  }

  frontend.register('learning', {
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
