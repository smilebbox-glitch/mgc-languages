/* v6.0.30 — Game World scene controller for Automotive Arcade. */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const GAME_WORLD = Object.freeze({
    match:{scene:'assembly',level:'Базовый',station:'Сборка',mission:'Термины'},
    listening:{scene:'assembly',level:'Базовый',station:'Линия',mission:'Аудио'},
    mistake:{scene:'quality',level:'Базовый',station:'Качество',mission:'Точность'},
    phrase:{scene:'assembly',level:'Средний',station:'Сборка',mission:'Фраза'},
    hotspot:{scene:'assembly',level:'Базовый',station:'Автомобиль',mission:'Детали'},
    assembly_order:{scene:'assembly',level:'Средний',station:'Сборка',mission:'Последовательность'},
    shop_route:{scene:'factory',level:'Средний',station:'Завод',mission:'Маршрут'},
    tool_select:{scene:'assembly',level:'Средний',station:'Сборка',mission:'Инструмент'},
    defect_detective:{scene:'paint',level:'Средний',station:'Окраска',mission:'Дефект'},
    safety_spot:{scene:'welding',level:'Средний',station:'Сварка',mission:'Безопасность'},
    quality_gate:{scene:'quality',level:'Продвинутый',station:'Качество',mission:'Quality Gate'},
    logistics_route:{scene:'logistics',level:'Средний',station:'Логистика',mission:'Матпоток'},
    kanban:{scene:'logistics',level:'Продвинутый',station:'Логистика',mission:'Kanban'},
    bom_builder:{scene:'engineering',level:'Продвинутый',station:'Инженерия',mission:'BOM'},
    spec_check:{scene:'quality',level:'Продвинутый',station:'Качество',mission:'Допуск'},
    rapid_recall:{scene:'factory',level:'Продвинутый',station:'Линия',mission:'Скорость'},
    memory_pairs:{scene:'assembly',level:'Базовый',station:'Garage',mission:'Память'},
    odd_one_out:{scene:'engineering',level:'Средний',station:'Инженерия',mission:'Логика'},
    dialogue_choice:{scene:'factory',level:'Продвинутый',station:'Совещание',mission:'Диалог'},
    shift_incident:{scene:'welding',level:'Продвинутый',station:'Смена',mission:'Инцидент'}
  });

  const SCENE_LABELS = Object.freeze({
    factory:'Factory Hub', assembly:'Сборка', welding:'Сварка', paint:'Окраска',
    logistics:'Логистика', quality:'Качество', engineering:'Инженерия'
  });

  let busy = false;
  let queued = false;

  function frontend() { return root.MGCFrontend || null; }
  function snapshot() {
    try {
      const f = frontend();
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }
  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }
  function activeGameType() {
    const s = snapshot();
    if (s.gameSessionV618 && s.gameSessionV618.game_type) return String(s.gameSessionV618.game_type);
    if (s.gameSession && s.gameSession.game_type) return String(s.gameSession.game_type);
    const head = main.querySelector('.game-lab-session[data-game-type]');
    return head ? String(head.dataset.gameType || '') : '';
  }
  function isGamesView() {
    if (root.document.querySelector('.nav-item.active[data-view="games"]')) return true;
    if (main.querySelector('[data-start-v618-game],[data-start-game],.game-lab-grid,.game-lab-session')) return true;
    return Boolean(activeGameType());
  }
  function currentWorld() {
    const type = activeGameType();
    if (type && GAME_WORLD[type]) return Object.assign({type:type}, GAME_WORLD[type]);
    return {type:'catalog',scene:'factory',level:'Выберите',station:'20 станций',mission:'Automotive Arcade'};
  }
  function stageHTML() {
    return '<div class="gw30-stage" aria-hidden="true">' +
      '<div class="gw30-ceiling"><i></i><i></i><i></i></div>' +
      '<div class="gw30-depth-grid"></div><div class="gw30-scan"></div>' +
      '<div class="gw30-robot gw30-left"><i></i><b></b></div>' +
      '<div class="gw30-robot gw30-right"><i></i><b></b></div>' +
      '<div class="gw30-conveyor"></div>' +
      '<div class="gw30-car"><div class="gw30-cabin"></div><div class="gw30-body"></div>' +
      '<i class="gw30-wheel gw30-wheel-a"></i><i class="gw30-wheel gw30-wheel-b"></i></div>' +
      '<div class="gw30-particles"><i></i><i></i><i></i><i></i><i></i><i></i></div>' +
      '</div>';
  }
  function hudHTML(world) {
    const s = snapshot();
    const language = s.language === 'chinese' ? '中文 · Putonghua' : 'English';
    const progress = main.querySelector('.game-session-progress,.page-head p');
    const progressText = progress ? progress.textContent.trim() : 'выберите игровую станцию';
    return '<section class="gw30-hud" aria-label="Game World">' +
      '<div class="gw30-hud-main"><span class="gw30-live"></span><div><small>GAME WORLD</small><b>' +
      esc(SCENE_LABELS[world.scene] || world.station) + '</b></div></div>' +
      '<div class="gw30-hud-chip"><small>ЗОНА</small><b>' + esc(world.station) + '</b></div>' +
      '<div class="gw30-hud-chip"><small>СЛОЖНОСТЬ</small><b>' + esc(world.level) + '</b></div>' +
      '<div class="gw30-hud-chip"><small>ЯЗЫК</small><b>' + esc(language) + '</b></div>' +
      '<div class="gw30-hud-chip gw30-mission"><small>МИССИЯ</small><b>' + esc(world.mission) + '</b><span>' + esc(progressText) + '</span></div>' +
      '</section>';
  }
  function decorateCatalog() {
    main.querySelectorAll('[data-start-v618-game],[data-start-game]').forEach(function (card) {
      const type = card.dataset.startV618Game || card.dataset.startGame || '';
      const world = GAME_WORLD[type];
      if (!world) return;
      card.dataset.gameWorld = world.scene;
      card.dataset.gameLevel = world.level;
      if (!card.querySelector('.gw30-card-meta')) {
        const meta = root.document.createElement('div');
        meta.className = 'gw30-card-meta';
        meta.innerHTML = '<span>' + esc(world.station) + '</span><span>' + esc(world.level) + '</span>';
        const copy = card.querySelector('.game-lab-copy') || card;
        copy.appendChild(meta);
      }
    });
  }
  function decorateQuestion(world) {
    const card = main.querySelector('.game-stage-card,.question-card,.game-question-card,.game-lab-session');
    if (!card || card.querySelector('.gw30-station-tag')) return;
    const tag = root.document.createElement('div');
    tag.className = 'gw30-station-tag';
    tag.innerHTML = '<span></span>' + esc(world.station) + ' · ' + esc(world.level);
    card.insertBefore(tag, card.firstChild);
  }
  function cleanup() {
    main.classList.remove('game-world-v630');
    main.removeAttribute('data-gw30-scene');
    main.querySelectorAll('.gw30-stage,.gw30-hud,.gw30-station-tag').forEach(function (node) { node.remove(); });
  }
  function decorate() {
    if (busy) return;
    busy = true;
    try {
      if (!isGamesView()) { cleanup(); return; }
      const world = currentWorld();
      main.classList.add('game-world-v630');
      main.dataset.gw30Scene = world.scene;
      if (!main.querySelector('.gw30-stage')) main.insertAdjacentHTML('afterbegin', stageHTML());
      const pageHead = main.querySelector('.page-head');
      if (pageHead && !main.querySelector('.gw30-hud')) pageHead.insertAdjacentHTML('afterend', hudHTML(world));
      decorateCatalog();
      decorateQuestion(world);
    } finally { busy = false; }
  }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; decorate(); });
  }

  new MutationObserver(schedule).observe(main,{childList:true,subtree:true});
  root.document.addEventListener('click',function (event) {
    if (event.target && event.target.closest && event.target.closest('[data-view="games"],[data-start-v618-game],[data-start-game],[data-go-games-home],[data-go="games"]')) {
      root.setTimeout(schedule,0);
    }
  });
  root.addEventListener('popstate',schedule);
  schedule();
})(window);
