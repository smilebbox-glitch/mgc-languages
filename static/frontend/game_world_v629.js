/* v6.0.29 — Game World UI decorator. No scoring, API or XP behavior is changed here. */
(function (root) {
  'use strict';

  const SCENES = Object.freeze({
    factory: {label: 'Factory Hub', detail: '4 игровые станции'},
    assembly: {label: 'Сборка', detail: 'Assembly line'},
    welding: {label: 'Сварка', detail: 'Body shop'},
    paint: {label: 'Окраска', detail: 'Paint shop'},
    logistics: {label: 'Логистика', detail: 'Material flow'}
  });
  const GAME_SCENES = Object.freeze({
    match: 'assembly',
    listening: 'welding',
    phrase: 'paint',
    mistake: 'logistics'
  });
  const KICKER_SCENES = Object.freeze({
    'Word Match': 'assembly',
    'Listening Sprint': 'welding',
    'Phrase Builder': 'paint',
    'Find the Mistake': 'logistics'
  });

  const main = root.document.getElementById('main');
  if (!main) return;

  let decorating = false;
  let scheduled = false;

  function activeGamesView() {
    const active = root.document.querySelector('.nav-item.active[data-view="games"]');
    return Boolean(active || main.querySelector('[data-start-game]') ||
      (main.querySelector('.question-card') && main.querySelector('.page-head .kicker')));
  }

  function currentSnapshot() {
    try {
      const frontend = root.MGCFrontend;
      if (!frontend || !frontend.has || !frontend.has('app-state')) return null;
      return frontend.get('app-state').current();
    } catch (_) {
      return null;
    }
  }

  function sceneFromTopic(topic) {
    const value = String(topic || '').toLowerCase();
    if (/свар|weld|焊/.test(value)) return 'welding';
    if (/окрас|paint|涂|喷/.test(value)) return 'paint';
    if (/логист|logistic|物流|仓/.test(value)) return 'logistics';
    if (/сбор|assembl|装配/.test(value)) return 'assembly';
    return '';
  }

  function detectScene() {
    if (main.querySelector('[data-start-game]')) return 'factory';
    const snapshot = currentSnapshot();
    const topicScene = sceneFromTopic(snapshot && snapshot.topic);
    if (topicScene) return topicScene;
    const kicker = main.querySelector('.page-head .kicker');
    const text = kicker ? kicker.textContent.trim() : '';
    return KICKER_SCENES[text] || 'assembly';
  }

  function backdropHTML() {
    return '<div class="game-world-backdrop" aria-hidden="true">' +
      '<div class="gw-overhead"></div><div class="gw-scanner"></div>' +
      '<div class="gw-robot left"></div><div class="gw-robot right"></div>' +
      '<div class="gw-conveyor"></div><div class="gw-vehicle">' +
      '<div class="gw-car-body"></div><div class="gw-wheel left"></div><div class="gw-wheel right"></div></div>' +
      '<div class="gw-particles"><i></i><i></i><i></i><i></i></div></div>';
  }

  function hudHTML(scene) {
    const info = SCENES[scene] || SCENES.factory;
    const snapshot = currentSnapshot() || {};
    const lang = snapshot.language === 'chinese' ? '中文 · Putonghua' : 'English';
    const indexText = main.querySelector('.page-head p') ? main.querySelector('.page-head p').textContent.trim() : '';
    return '<div class="game-world-hud" aria-label="Игровая производственная сцена">' +
      '<div class="gw-hud-title"><span class="gw-live-dot"></span><span>' + info.label + ' · ' + info.detail + '</span></div>' +
      '<span class="gw-hud-chip"><b>Язык</b> ' + lang + '</span>' +
      '<span class="gw-hud-chip"><b>Режим</b> Adaptive</span>' +
      '<span class="gw-hud-chip"><b>Миссия</b> ' + (indexText || 'выберите станцию') + '</span></div>';
  }

  function decorateCards() {
    root.document.querySelectorAll('#main [data-start-game]').forEach(function (button) {
      const type = button.dataset.startGame;
      button.dataset.gameWorld = GAME_SCENES[type] || 'assembly';
      button.setAttribute('aria-label', (button.querySelector('h3') ? button.querySelector('h3').textContent : 'Игра') + ', производственная игровая станция');
    });
  }

  function addStationTag(scene) {
    if (scene === 'factory') return;
    const card = main.querySelector('.question-card');
    if (!card || card.querySelector('.gw-station-tag')) return;
    const tag = root.document.createElement('div');
    tag.className = 'gw-station-tag';
    tag.textContent = (SCENES[scene] || SCENES.assembly).label + ' · рабочая ситуация';
    card.insertBefore(tag, card.firstChild);
  }

  function cleanup() {
    main.classList.remove('game-world-v629');
    main.removeAttribute('data-game-scene');
    main.querySelectorAll('.game-world-backdrop,.game-world-hud,.gw-station-tag').forEach(function (node) {
      node.remove();
    });
  }

  function decorate() {
    if (decorating) return;
    decorating = true;
    try {
      if (!activeGamesView()) {
        cleanup();
        return;
      }
      const scene = detectScene();
      main.classList.add('game-world-v629');
      main.dataset.gameScene = scene;

      if (!main.querySelector('.game-world-backdrop')) {
        main.insertAdjacentHTML('afterbegin', backdropHTML());
      }
      const head = main.querySelector('.page-head');
      if (head && !main.querySelector('.game-world-hud')) {
        head.insertAdjacentHTML('afterend', hudHTML(scene));
      }
      decorateCards();
      addStationTag(scene);
    } finally {
      decorating = false;
    }
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    root.requestAnimationFrame(function () {
      scheduled = false;
      decorate();
    });
  }

  new MutationObserver(schedule).observe(main, {childList: true, subtree: true});
  root.document.addEventListener('click', function (event) {
    if (event.target && event.target.closest && event.target.closest('[data-view="games"],[data-start-game],[data-go="games"]')) {
      root.setTimeout(schedule, 0);
    }
  });
  root.addEventListener('popstate', schedule);
  root.addEventListener('resize', schedule, {passive: true});
  schedule();
})(window);
