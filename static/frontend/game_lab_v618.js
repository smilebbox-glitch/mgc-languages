/* v6.0.18: automotive game lab — 20 distinct, data-driven learning games. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('game-lab-v618')) return;

  const GAME_CATALOG = Object.freeze([
    {id:'match', title:'Word Match', desc:'Термин ↔ точный перевод', icon:'↔', group:'Слова', tone:'blue'},
    {id:'listening', title:'Listening Sprint', desc:'Услышать термин и распознать смысл', icon:'◖', group:'Аудио', tone:'cyan'},
    {id:'mistake', title:'Precision Check', desc:'Найти единственное точное значение', icon:'✓', group:'Слова', tone:'green'},
    {id:'phrase', title:'Phrase Builder', desc:'Собрать рабочую фразу', icon:'≡', group:'Фразы', tone:'violet'},
    {id:'hotspot', title:'Car Part Hotspot', desc:'Найти деталь прямо на схеме автомобиля', icon:'◎', group:'Визуальные', tone:'orange', featured:true},
    {id:'assembly_order', title:'Build the Car', desc:'Восстановить технологическую последовательность', icon:'▥', group:'Производство', tone:'navy'},
    {id:'shop_route', title:'Factory Router', desc:'Отправить термин в правильный цех', icon:'⌘', group:'Производство', tone:'teal'},
    {id:'tool_select', title:'Tool Selector', desc:'Выбрать инструмент под рабочую задачу', icon:'⌁', group:'Производство', tone:'amber'},
    {id:'defect_detective', title:'Defect Detective', desc:'Опознать дефект по визуальному паттерну', icon:'⌕', group:'Качество', tone:'red', featured:true},
    {id:'safety_spot', title:'Safety Spot', desc:'Заметить опасность на рабочем месте', icon:'△', group:'Безопасность', tone:'yellow'},
    {id:'quality_gate', title:'Quality Gate', desc:'PASS / REWORK / HOLD по измерениям', icon:'◆', group:'Качество', tone:'green'},
    {id:'logistics_route', title:'Logistics Flow', desc:'Собрать правильный материальный поток', icon:'⇢', group:'Логистика', tone:'blue'},
    {id:'kanban', title:'Kanban Challenge', desc:'Принять решение о пополнении', icon:'▦', group:'Логистика', tone:'orange'},
    {id:'bom_builder', title:'Build the BOM', desc:'Привязать компонент к подсистеме', icon:'⊞', group:'Инженерия', tone:'violet'},
    {id:'spec_check', title:'Spec or NOK?', desc:'Сравнить факт с допуском', icon:'±', group:'Качество', tone:'cyan'},
    {id:'rapid_recall', title:'10-Second Recall', desc:'Быстрый выбор под таймер', icon:'10', group:'Скорость', tone:'red'},
    {id:'memory_pairs', title:'Memory Garage', desc:'Открыть правильную карточку-пару', icon:'▣', group:'Память', tone:'violet'},
    {id:'odd_one_out', title:'Odd One Out', desc:'Найти термин из другой группы', icon:'◫', group:'Логика', tone:'teal'},
    {id:'dialogue_choice', title:'Dialogue Duel', desc:'Выбрать профессиональную реплику', icon:'“”', group:'Коммуникация', tone:'navy', featured:true},
    {id:'shift_incident', title:'Shift Incident', desc:'Принять решение в реальной сменной ситуации', icon:'!', group:'Сценарии', tone:'red', featured:true}
  ]);

  let installed = false;
  let rapidTimer = null;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function toast(message) { legacy().toast(String(message || '')); }

  function owns(view) { return String(view || '') === 'games'; }

  function featureEnabled() {
    const flags = (current().pilot && current().pilot.features) || {};
    return flags.games !== false;
  }

  function pageHead(kicker, title, subtitle) {
    return '<div class="page-head game-lab-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function catalogItem(id) {
    return GAME_CATALOG.find(function (item) { return item.id === id; }) || GAME_CATALOG[0];
  }

  function updateXp(profile) {
    if (!profile) return;
    state().set('gamification', profile);
    const pill = query('#xpPill');
    if (pill) pill.textContent = Number(profile.spendable_xp || 0) + ' XP';
  }

  function clearRapidTimer() {
    if (rapidTimer) root.clearTimeout(rapidTimer);
    rapidTimer = null;
  }

  function renderCatalog() {
    clearRapidTimer();
    const main = query('#main');
    if (!main) return;
    const groups = Array.from(new Set(GAME_CATALOG.map(function (game) { return game.group; })));
    main.innerHTML = pageHead(
      'MGC AUTOMOTIVE ARCADE · 20 ИГР',
      'Игровая практика для автопрома',
      'Не один и тот же тест в разных оболочках: визуальные детали автомобиля, производство, качество, логистика, безопасность, коммуникация и скорость.'
    ) + '<div class="game-lab-summary"><div><b>20</b><span>разных механик</span></div>' +
      '<div><b>5</b><span>ответов за сессию</span></div><div><b>2</b><span>языка</span></div>' +
      '<div><b>∞</b><span>вариаций из словаря</span></div></div>' +
      '<div class="game-filter-row"><button class="game-filter active" data-game-filter="Все">Все</button>' +
      groups.map(function (group) { return '<button class="game-filter" data-game-filter="' + esc(group) + '">' + esc(group) + '</button>'; }).join('') +
      '</div><div id="gameCatalogGrid" class="game-lab-grid">' + renderGameCards(GAME_CATALOG) + '</div>';

    queryAll('[data-start-v618-game]').forEach(function (button) {
      button.addEventListener('click', function () { void startGame(button.dataset.startV618Game); });
    });
    queryAll('[data-game-filter]').forEach(function (button) {
      button.addEventListener('click', function () {
        queryAll('[data-game-filter]').forEach(function (value) { value.classList.toggle('active', value === button); });
        const filter = button.dataset.gameFilter;
        const games = filter === 'Все' ? GAME_CATALOG : GAME_CATALOG.filter(function (game) { return game.group === filter; });
        const grid = query('#gameCatalogGrid');
        if (grid) grid.innerHTML = renderGameCards(games);
        queryAll('[data-start-v618-game]').forEach(function (start) {
          start.addEventListener('click', function () { void startGame(start.dataset.startV618Game); });
        });
      });
    });
  }

  function renderGameCards(games) {
    return games.map(function (game) {
      return '<button class="game-lab-card tone-' + esc(game.tone) + (game.featured ? ' featured' : '') +
        '" data-start-v618-game="' + esc(game.id) + '"><div class="game-lab-icon">' + esc(game.icon) +
        '</div><div class="game-lab-copy"><span class="game-lab-group">' + esc(game.group) +
        '</span><h3>' + esc(game.title) + '</h3><p>' + esc(game.desc) +
        '</p></div><span class="game-lab-start">Играть →</span></button>';
    }).join('');
  }

  async function startGame(type) {
    try {
      if (!featureEnabled()) throw new Error('Игры пока не включены для вашей волны пилота');
      const snapshot = current();
      const url = '/api/games/' + encodeURIComponent(type) + '/start?language=' +
        encodeURIComponent(snapshot.language) + '&topic=' + encodeURIComponent(snapshot.topic || '');
      const session = await api().request(url, {method:'POST'});
      state().patch({gameSessionV618:session, gameAnswersV618:[], gameIndexV618:0, gameSelectionV618:[]});
      await renderSession();
    } catch (error) {
      toast(error && error.message ? error.message : error);
      if (frontend.has('error-boundary')) frontend.get('error-boundary').record('game-lab-start', error && error.message ? error.message : error, '', 0, 0);
    }
  }

  async function finishGame(session) {
    clearRapidTimer();
    const result = await api().request('/api/games/' + encodeURIComponent(session.session_id) + '/finish', {
      method:'POST', body:JSON.stringify({answers:current().gameAnswersV618 || []})
    });
    if (result.profile) updateXp(result.profile);
    state().patch({gameSessionV618:null, gameAnswersV618:[], gameIndexV618:0, gameSelectionV618:[]});
    const main = query('#main');
    if (!main) return;
    const perfect = Number(result.score || 0) === Number(result.total || 0);
    main.innerHTML = pageHead('СЕССИЯ ЗАВЕРШЕНА', perfect ? 'Идеальный заезд' : 'Практика завершена',
      'Пять ответов — и стоп. Результат нужен для обучения, а не для бесконечного фарма XP.') +
      '<section class="game-result-panel"><div class="game-result-score">' + Number(result.score || 0) +
      '<small>/ ' + Number(result.total || 0) + '</small></div><div><h2>' + (perfect ? '5/5 — без ошибок' : 'Следующая попытка будет другой') +
      '</h2><p>Начислено <b>+' + Number(result.awarded || 0) + ' XP</b>. Сервер ограничивает повторный фарм.</p></div>' +
      '<div class="game-result-actions"><button class="primary" data-go-games-home>Выбрать другую игру</button>' +
      '<button class="ghost" data-replay-v618="' + esc(session.game_type) + '">Повторить механику</button></div></section>';
    const home = query('[data-go-games-home]');
    if (home) home.addEventListener('click', renderCatalog);
    const replay = query('[data-replay-v618]');
    if (replay) replay.addEventListener('click', function () { void startGame(replay.dataset.replayV618); });
  }

  function submitAnswer(answer) {
    clearRapidTimer();
    const answers = (current().gameAnswersV618 || []).slice();
    answers.push(answer);
    state().patch({gameAnswersV618:answers, gameIndexV618:Number(current().gameIndexV618 || 0) + 1, gameSelectionV618:[]});
    void renderSession();
  }

  function choiceButtons(item, className) {
    const options = item.options || item.cards || [];
    return '<div class="game-choice-grid ' + esc(className || '') + '">' + options.map(function (value, index) {
      return '<button class="game-choice" data-v618-choice="' + index + '"><span>' + esc(value) + '</span></button>';
    }).join('') + '</div>';
  }

  function carSvg() {
    return '<div class="car-hotspot-stage" aria-label="Схема автомобиля">' +
      '<svg viewBox="0 0 760 330" role="img" aria-label="Автомобиль — выберите деталь">' +
      '<path class="car-body" d="M120 220 L145 150 Q180 100 280 92 L455 92 Q525 100 585 160 L665 180 Q700 190 708 225 L690 252 L105 252 Q82 240 90 220 Z"/>' +
      '<path class="car-window" d="M285 108 L448 108 Q490 112 535 160 L270 160 Z"/>' +
      '<circle class="car-wheel" cx="210" cy="248" r="48"/><circle class="car-wheel" cx="580" cy="248" r="48"/>' +
      '<rect class="car-door-line" x="340" y="166" width="150" height="77" rx="8"/>' +
      '<button class="svg-hotspot" data-hotspot-zone="hood" aria-label="Капот"><circle cx="565" cy="174" r="23"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="windshield" aria-label="Ветровое стекло"><circle cx="475" cy="132" r="22"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="mirror" aria-label="Зеркало"><circle cx="508" cy="160" r="20"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="door" aria-label="Дверь"><circle cx="414" cy="205" r="25"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="fender" aria-label="Крыло"><circle cx="620" cy="211" r="22"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="headlamp" aria-label="Фара"><circle cx="660" cy="195" r="19"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="bumper" aria-label="Бампер"><circle cx="690" cy="231" r="18"/></button>' +
      '<button class="svg-hotspot" data-hotspot-zone="wheel" aria-label="Колесо"><circle cx="580" cy="248" r="25"/></button>' +
      '</svg><div class="hotspot-hint">Нажмите на нужную зону</div></div>';
  }

  function defectVisual(code) {
    const labels = {
      'scratch':'царапина', 'dent':'вмятина', 'orange-peel':'апельсиновая корка', 'paint-run':'подтек',
      'pinhole':'пора', 'weld-spatter':'сварочные брызги', 'gap':'зазор', 'flush':'перепад'
    };
    return '<div class="defect-visual defect-' + esc(code) + '"><div class="defect-panel"><i></i><i></i><i></i></div>' +
      '<span>Visual inspection</span><small>' + esc(labels[code] || 'дефект') + '</small></div>';
  }

  function safetyVisual(code) {
    return '<div class="safety-visual safety-' + esc(code) + '"><div class="factory-floor"><span class="machine">MACHINE</span>' +
      '<span class="worker">●<i></i></span><span class="forklift">▰</span><span class="warning">!</span></div>' +
      '<small>Найдите опасный фактор</small></div>';
  }

  function factoryRoute(item) {
    const shops = [
      ['stamping','Штамповка'], ['welding','Сварка'], ['paint','Окраска'], ['assembly','Сборка'], ['quality','Качество'], ['logistics','Логистика']
    ];
    return '<div class="factory-route"><div class="route-term">' + esc(item.term || '') + '</div><div class="factory-line">' +
      shops.map(function (shop) { return '<span class="factory-node node-' + shop[0] + '">' + shop[1] + '</span>'; }).join('<b>→</b>') +
      '</div></div>';
  }

  function metricsVisual(item, mode) {
    if (mode === 'kanban') {
      return '<div class="kanban-board"><div><span>Остаток</span><b>' + Number(item.stock || 0) + '</b></div>' +
        '<div><span>Точка заказа</span><b>' + Number(item.trigger || 0) + '</b></div><div class="kanban-signal">KANBAN</div></div>';
    }
    if (mode === 'quality-gate') {
      return '<div class="quality-gauge"><span>' + Number(item.low || 0) + '</span><div class="gauge-track"><i style="left:52%"></i></div>' +
        '<span>' + Number(item.high || 0) + '</span><b>Факт ' + Number(item.actual || 0) + '</b></div>';
    }
    return '<div class="spec-card"><span>SPEC</span><b>' + esc(item.prompt || '') + '</b><i>±</i></div>';
  }

  function renderOrder(item) {
    const selected = Array.isArray(current().gameSelectionV618) ? current().gameSelectionV618 : [];
    const tokens = item.tokens || [];
    return '<div class="order-track"><div class="order-built">' +
      (selected.length ? selected.map(function (value, index) { return '<span><b>' + (index + 1) + '</b>' + esc(value) + '</span>'; }).join('') : '<em>Выберите первый этап</em>') +
      '</div><div class="order-bank">' + tokens.map(function (value, index) {
        const used = selected.indexOf(value) !== -1;
        return '<button data-order-token="' + index + '"' + (used ? ' disabled' : '') + '>' + esc(value) + '</button>';
      }).join('') + '</div><div class="game-inline-actions"><button class="ghost" data-order-reset>Сбросить</button>' +
      '<button class="primary" data-order-done' + (selected.length !== tokens.length ? ' disabled' : '') + '>Готово</button></div></div>';
  }

  function bodyFor(item, type) {
    const kind = item.kind || 'choice';
    if (kind === 'hotspot') {
      return '<div class="hotspot-question"><div class="hotspot-target"><span>Найдите</span><b>' + esc(item.target) +
        '</b><small>' + esc(item.translation || '') + '</small></div>' + carSvg() + '</div>';
    }
    if (kind === 'order') {
      return '<div class="game-prompt-block"><h2>' + esc(item.prompt || '') + '</h2><p>' + esc(item.translation || '') + '</p></div>' + renderOrder(item);
    }
    if (kind === 'defect') {
      return defectVisual(item.visual) + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'defect-options');
    }
    if (kind === 'safety') {
      return safetyVisual(item.visual) + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'safety-options');
    }
    if (kind === 'shop-route') {
      return factoryRoute(item) + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'shop-options');
    }
    if (kind === 'tool') {
      return '<div class="tool-rack"><span>🔧</span><span>⌁</span><span>⊣</span><span>▱</span></div><h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'tool-options');
    }
    if (kind === 'quality-gate') {
      return metricsVisual(item, kind) + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'gate-options');
    }
    if (kind === 'kanban') {
      return metricsVisual(item, kind) + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'kanban-options');
    }
    if (kind === 'spec') {
      return metricsVisual(item, kind) + choiceButtons(item, 'spec-options');
    }
    if (kind === 'bom') {
      return '<div class="bom-tree"><span>VEHICLE</span><b>└─ ?</b><strong>' + esc(item.term || '') + '</strong></div><h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'bom-options');
    }
    if (kind === 'memory') {
      return '<div class="memory-term"><span>Найдите пару для</span><b>' + esc(item.term || '') + '</b></div>' +
        '<div class="memory-grid">' + (item.cards || []).map(function (value, index) {
          return '<button class="memory-card" data-v618-choice="' + index + '"><span class="memory-back">MGC</span><span class="memory-front">' + esc(value) + '</span></button>';
        }).join('') + '</div>';
    }
    if (kind === 'dialogue' || kind === 'incident') {
      return '<div class="scenario-console ' + kind + '"><div class="scenario-console-top"><span>' +
        (kind === 'incident' ? 'SHIFT INCIDENT' : 'DIALOGUE DUEL') + '</span><i>LIVE</i></div><h2>' + esc(item.prompt || '') +
        '</h2>' + choiceButtons(item, 'scenario-decisions') + '</div>';
    }
    if (kind === 'rapid') {
      return '<div class="rapid-clock"><span>10</span><small>SEC</small></div><h2>' + esc(item.term || '') + '</h2>' +
        (item.pronunciation ? '<p class="question-pinyin">' + esc(item.pronunciation) + '</p>' : '') + choiceButtons(item, 'rapid-options');
    }
    if (kind === 'listening') {
      return '<div class="listening-radar"><button data-play-v618-audio>▶</button><i></i><i></i><i></i></div><h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, 'audio-options');
    }
    const term = item.term ? '<div class="game-term-display"><b>' + esc(item.term) + '</b>' +
      (item.pronunciation ? '<span class="question-pinyin">' + esc(item.pronunciation) + '</span>' : '') + '</div>' : '';
    return term + '<h2>' + esc(item.prompt || '') + '</h2>' + choiceButtons(item, kind === 'odd' ? 'odd-options' : '');
  }

  async function renderSession() {
    clearRapidTimer();
    const snapshot = current();
    const session = snapshot.gameSessionV618;
    if (!session) { renderCatalog(); return; }
    const items = session.items || [];
    const index = Number(snapshot.gameIndexV618 || 0);
    if (index >= items.length) { await finishGame(session); return; }

    const item = items[index];
    const catalog = catalogItem(session.game_type);
    const main = query('#main');
    if (!main) return;
    main.innerHTML = pageHead(catalog.group, catalog.title, catalog.desc) +
      '<div class="game-session-shell tone-' + esc(catalog.tone) + '"><div class="game-session-top"><button class="ghost mini" data-exit-v618>← Все игры</button>' +
      '<div class="game-stepper"><span>' + (index + 1) + ' / ' + items.length + '</span><div><i style="width:' + (((index + 1) / items.length) * 100) + '%"></i></div></div>' +
      '<span class="five-answer-badge">max 5</span></div><section class="game-stage kind-' + esc(item.kind || 'choice') + '">' +
      bodyFor(item, session.game_type) + '</section></div>';

    const exit = query('[data-exit-v618]');
    if (exit) exit.addEventListener('click', function () {
      clearRapidTimer(); state().patch({gameSessionV618:null, gameAnswersV618:[], gameIndexV618:0, gameSelectionV618:[]}); renderCatalog();
    });

    queryAll('[data-v618-choice]').forEach(function (button) {
      button.addEventListener('click', function () {
        if (button.classList.contains('memory-card')) button.classList.add('flipped');
        root.setTimeout(function () { submitAnswer(Number(button.dataset.v618Choice)); }, button.classList.contains('memory-card') ? 280 : 0);
      });
    });
    queryAll('[data-hotspot-zone]').forEach(function (button) {
      button.addEventListener('click', function () { submitAnswer(button.dataset.hotspotZone); });
    });
    queryAll('[data-order-token]').forEach(function (button) {
      button.addEventListener('click', function () {
        const selected = (current().gameSelectionV618 || []).slice();
        selected.push(item.tokens[Number(button.dataset.orderToken)]);
        state().set('gameSelectionV618', selected);
        void renderSession();
      });
    });
    const reset = query('[data-order-reset]');
    if (reset) reset.addEventListener('click', function () { state().set('gameSelectionV618', []); void renderSession(); });
    const done = query('[data-order-done]');
    if (done) done.addEventListener('click', function () { submitAnswer((current().gameSelectionV618 || []).slice()); });
    const audio = query('[data-play-v618-audio]');
    if (audio) audio.addEventListener('click', function () { void legacy().playPronunciation(item.audio_text || item.term || '', 0.82, current().language); });

    if ((item.kind || '') === 'rapid') {
      const clock = query('.rapid-clock span');
      let seconds = Number(item.seconds || 10);
      const tick = function () {
        if (clock) clock.textContent = String(seconds);
        if (seconds <= 0) { submitAnswer(-1); return; }
        seconds -= 1;
        rapidTimer = root.setTimeout(tick, 1000);
      };
      tick();
    }
  }

  async function render() {
    if (!featureEnabled()) throw new Error('Игры пока не включены для вашей волны пилота');
    if (current().gameSessionV618) await renderSession();
    else renderCatalog();
    legacy().ensureChineseStandardBanner();
  }

  async function navigate(view) {
    if (!owns(view)) return legacy().setView(view);
    state().set('view', 'games');
    legacy().closeMenu();
    queryAll('[data-view]').forEach(function (button) { button.classList.toggle('active', button.dataset.view === 'games'); });
    const main = query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка игровых механик</p></div>';
    await render();
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view="games"]') : null;
      if (!button) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate('games').catch(function (error) { toast(error && error.message ? error.message : error); });
    }, true);
  }

  frontend.register('game-lab-v618', {
    views:['games'],
    catalog:GAME_CATALOG,
    owns:owns,
    render:render,
    navigate:navigate,
    startGame:startGame,
    install:install
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
