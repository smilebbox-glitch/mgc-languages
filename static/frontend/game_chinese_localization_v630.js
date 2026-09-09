/* v6.0.30 — Russian game UI with target-language learning content.
 * Game names, descriptions, buttons, XP/progress and production chrome stay Russian.
 * The selected language is reserved for the material being learned; canonical answers stay untouched.
 */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const GAME_TITLES_RU = Object.freeze({
    match:'Сопоставление слов', listening:'Аудиоспринт', mistake:'Точная проверка',
    phrase:'Конструктор фраз', hotspot:'Детали автомобиля', assembly_order:'Собери автомобиль',
    shop_route:'Маршрут по заводу', tool_select:'Выбор инструмента', defect_detective:'Детектор дефектов',
    safety_spot:'Найди опасность', quality_gate:'Контроль качества', logistics_route:'Логистический поток',
    kanban:'Канбан', bom_builder:'Собери BOM', spec_check:'Допуск или NOK?', rapid_recall:'Быстрый ответ',
    memory_pairs:'Гараж памяти', odd_one_out:'Лишний термин', dialogue_choice:'Рабочий диалог',
    shift_incident:'Ситуация на смене'
  });

  const STATIC_RU = Object.freeze({
    'MGC AUTOMOTIVE ARCADE · 20 ИГР':'MGC АВТОМОБИЛЬНЫЕ ИГРЫ · 20 ИГР',
    'ARCADE MASTERY · SKILL MAP':'ИГРОВОЙ ПРОФИЛЬ · КАРТА НАВЫКОВ',
    'GAME WORLD':'ИГРОВОЙ МИР', 'Factory Hub':'Центр завода', 'Automotive Arcade':'Автомобильные игры',
    'Garage':'Гараж', 'MISSION BRIEFING':'ИНСТРУКТАЖ', 'MISSION FLOW':'ХОД ЗАДАНИЯ',
    'MISSION COMPLETE':'ЗАДАНИЕ ЗАВЕРШЕНО', 'PASS':'ГОДЕН', 'REWORK':'ДОРАБОТКА', 'HOLD':'УДЕРЖАНИЕ',
    'ASSEMBLY LINE · LIVE':'СБОРОЧНАЯ ЛИНИЯ · РАБОТАЕТ', 'LINE RUNNING':'ЛИНИЯ РАБОТАЕТ',
    'BODY SHOP · ROBOT CELL':'СВАРОЧНЫЙ ЦЕХ · РОБОТ-ЯЧЕЙКА', 'CELL SAFE':'ЯЧЕЙКА БЕЗОПАСНА',
    'PAINT SHOP · INSPECTION':'ОКРАСКА · КОНТРОЛЬ', 'INSPECTION ACTIVE':'КОНТРОЛЬ ИДЁТ',
    'INTRALOGISTICS · MATERIAL FLOW':'ВНУТРИЗАВОДСКАЯ ЛОГИСТИКА · МАТЕРИАЛЬНЫЙ ПОТОК',
    'FLOW SYNCHRONIZED':'ПОТОК СИНХРОНИЗИРОВАН', 'QUALITY GATE':'КОНТРОЛЬ КАЧЕСТВА',
    'SPEC CHECK':'ПРОВЕРКА ДОПУСКА', 'PRECISION':'ТОЧНАЯ ПРОВЕРКА', 'NOMINAL':'НОМИНАЛ',
    'MEASUREMENT LIVE':'ИЗМЕРЕНИЕ ИДЁТ', 'BOM DIGITAL THREAD':'ЦИФРОВАЯ ЦЕПОЧКА BOM',
    'ENGINEERING CLASSIFICATION':'ИНЖЕНЕРНАЯ КЛАССИФИКАЦИЯ', 'ENGINEERING':'ИНЖЕНЕРИЯ',
    'A3 DRAWING':'ЧЕРТЁЖ A3', 'REV':'РЕВИЗИЯ', 'DIGITAL THREAD LINKED':'ЦИФРОВАЯ ЦЕПОЧКА СВЯЗАНА',
    'PROCESS LIVE':'ПРОЦЕСС ИДЁТ', 'TORQUE VERIFY':'ПРОВЕРКА МОМЕНТА',
    'SAFETY INTERLOCK':'БЛОКИРОВКА БЕЗОПАСНОСТИ', 'AGV ROUTE':'МАРШРУТ AGV',
    'CMM PROBE':'ЩУП CMM', 'CONTROL ROOM':'ДИСПЕТЧЕРСКАЯ', 'PART INSTALL':'УСТАНОВКА ДЕТАЛИ',
    'SURFACE SCAN':'СКАН ПОВЕРХНОСТИ', 'LIVE':'В РАБОТЕ', 'SEC':'СЕК', 'SPEC':'ДОПУСК',
    'VEHICLE':'АВТОМОБИЛЬ', 'BODY':'КУЗОВ', 'MODULE':'МОДУЛЬ', 'COMPONENT':'КОМПОНЕНТ',
    'MASTER':'МАСТЕР', 'EXPERT':'ЭКСПЕРТ', 'SPECIALIST':'СПЕЦИАЛИСТ', 'OPERATOR':'ОПЕРАТОР',
    'DEVELOPING':'В РАЗВИТИИ', 'ROOKIE':'НОВИЧОК', 'TRAINED':'ПРОЙДЕНО',
    'ACTIVE INCIDENT':'ТЕКУЩАЯ СИТУАЦИЯ', 'READY':'ГОТОВО', 'PENDING':'ОЖИДАЕТ',
    'ACTION':'В РАБОТЕ', 'WAIT':'ОЖИДАЕТ', 'XP economy':'XP И ПРОГРЕСС', 'Lifetime:':'Всего XP:',

    /* Undo former Chinese UI-only translations. Learning text is excluded below. */
    '游戏能力 · 技能图谱':'ИГРОВОЙ ПРОФИЛЬ · КАРТА НАВЫКОВ', '任务简报':'ИНСТРУКТАЖ',
    '任务进度':'ХОД ЗАДАНИЯ', '任务完成':'ЗАДАНИЕ ЗАВЕРШЕНО', '游戏世界':'ИГРОВОЙ МИР',
    '工厂中心':'Центр завода', '汽车工厂游戏':'Автомобильные игры', '车库':'Гараж',
    '总装线 · 运行中':'СБОРОЧНАЯ ЛИНИЯ · РАБОТАЕТ', '生产线运行中':'ЛИНИЯ РАБОТАЕТ',
    '焊装车间 · 机器人单元':'СВАРОЧНЫЙ ЦЕХ · РОБОТ-ЯЧЕЙКА', '单元安全':'ЯЧЕЙКА БЕЗОПАСНА',
    '涂装车间 · 检查':'ОКРАСКА · КОНТРОЛЬ', '检查进行中':'КОНТРОЛЬ ИДЁТ',
    '厂内物流 · 物料流':'ВНУТРИЗАВОДСКАЯ ЛОГИСТИКА · МАТЕРИАЛЬНЫЙ ПОТОК', '物流同步':'ПОТОК СИНХРОНИЗИРОВАН',
    '质量关':'КОНТРОЛЬ КАЧЕСТВА', '规格检查':'ПРОВЕРКА ДОПУСКА', '精准检查':'ТОЧНАЯ ПРОВЕРКА',
    '名义值':'НОМИНАЛ', '测量进行中':'ИЗМЕРЕНИЕ ИДЁТ', '物料清单数字线程':'ЦИФРОВАЯ ЦЕПОЧКА BOM',
    '工程分类':'ИНЖЕНЕРНАЯ КЛАССИФИКАЦИЯ', 'A3 图纸':'ЧЕРТЁЖ A3', '版本':'РЕВИЗИЯ',
    '数字线程已连接':'ЦИФРОВАЯ ЦЕПОЧКА СВЯЗАНА', '生产过程 · 运行中':'ПРОЦЕСС ИДЁТ',
    '扭矩确认':'ПРОВЕРКА МОМЕНТА', '安全联锁':'БЛОКИРОВКА БЕЗОПАСНОСТИ', 'AGV 路线':'МАРШРУТ AGV',
    '三坐标测头':'ЩУП CMM', '控制室':'ДИСПЕТЧЕРСКАЯ', '部件安装':'УСТАНОВКА ДЕТАЛИ', '表面扫描':'СКАН ПОВЕРХНОСТИ'
  });

  const STAGE_RU = Object.freeze({
    supplier:'Поставщик', logistics:'Логистика', welding:'Сварка', paint:'Окраска',
    assembly:'Сборка', quality:'Качество', engineering:'Инженерия'
  });

  let queued = false;

  function snapshot() {
    try {
      const f = root.MGCFrontend;
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }

  function activeGameType() {
    const state = snapshot();
    const session = state.gameSessionV618 || state.gameSession || null;
    return session && session.game_type ? String(session.game_type) : '';
  }

  function isLearningNode(node) {
    const parent = node && node.parentElement;
    return Boolean(parent && parent.closest(
      '.game-choice,.game-stage h2,.game-term-display,.hotspot-target,.order-track,.memory-card,' +
      '.scenario-decisions,.question-pinyin,.pinyin-line,.reading-line,.spec-card b,.bom-tree strong,' +
      '.fj2-incident-main,.fj2-pinyin,.fj2-incident-helper'
    ));
  }

  function russianStaticText() {
    const walker = root.document.createTreeWalker(main, root.NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (node) {
      if (isLearningNode(node)) return;
      const raw = String(node.nodeValue || '');
      const core = raw.trim();
      if (!core || !Object.prototype.hasOwnProperty.call(STATIC_RU, core)) return;
      node.nodeValue = raw.replace(core, STATIC_RU[core]);
    });
  }

  function russianCatalogTitles() {
    main.querySelectorAll('[data-start-v618-game],[data-start-game]').forEach(function (card) {
      const type = String(card.dataset.startV618Game || card.dataset.startGame || '');
      const title = card.querySelector('h3');
      if (title && GAME_TITLES_RU[type]) title.textContent = GAME_TITLES_RU[type];
      card.querySelectorAll('.gw30-zh-title-pinyin').forEach(function (node) { node.remove(); });
    });
  }

  function russianActiveTitle() {
    const type = activeGameType();
    const title = main.querySelector('.page-head h1');
    if (title && type && GAME_TITLES_RU[type]) title.textContent = GAME_TITLES_RU[type];
    main.querySelectorAll('.gw30-zh-title-pinyin').forEach(function (node) { node.remove(); });
  }

  function russianJourneyChrome() {
    main.querySelectorAll('[data-fj2-stage]').forEach(function (button) {
      const id = String(button.dataset.fj2Stage || '');
      const label = button.querySelector('.fj2-route-label b');
      const helper = button.querySelector('.fj2-route-label small');
      if (label && STAGE_RU[id]) label.textContent = STAGE_RU[id];
      if (helper) helper.textContent = '';
    });
    const rows = Array.from(main.querySelectorAll('.fj2-twin-row'));
    Object.keys(STAGE_RU).forEach(function (id, index) {
      const label = rows[index] && rows[index].querySelector('span');
      if (label) label.textContent = STAGE_RU[id];
    });
  }

  function mark() {
    main.setAttribute('data-game-ui-language', 'ru');
    main.setAttribute('data-game-learning-language', snapshot().language === 'chinese' ? 'zh-pinyin' : 'en');
  }

  function apply() {
    mark();
    russianCatalogTitles();
    russianActiveTitle();
    russianJourneyChrome();
    russianStaticText();
  }

  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; apply(); });
  }

  new MutationObserver(schedule).observe(main, {childList:true, subtree:true, characterData:true});
  root.document.addEventListener('click', function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-language],[data-view="games"],[data-view="xp"],[data-start-v618-game],[data-start-game],[data-fj2-stage]')) {
      root.setTimeout(schedule, 0);
      root.setTimeout(schedule, 120);
    }
  }, true);
  root.addEventListener('popstate', schedule);
  schedule();
})(window);
