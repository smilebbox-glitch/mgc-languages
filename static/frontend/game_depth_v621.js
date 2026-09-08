/* v6.0.21: production game depth — richer automotive scenes and progressive difficulty. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('game-depth-v621')) return;

  const STORAGE_KEY = 'mgc.game-depth.v621.difficulty';
  const LEVELS = Object.freeze({
    adaptive: {label:'Адаптивно', short:'AUTO', caption:'Сложность растёт по ходу 5 вопросов'},
    training: {label:'Учебный', short:'1', caption:'Больше контекста и визуальных ориентиров'},
    shift: {label:'Смена', short:'2', caption:'Рабочая ситуация без лишних подсказок'},
    expert: {label:'Эксперт', short:'3', caption:'Минимум подсказок, выше визуальная сложность'}
  });

  const GAME_SCENES = Object.freeze({
    match:'assembly', listening:'assembly', mistake:'quality', phrase:'meeting', hotspot:'vehicle',
    assembly_order:'assembly', shop_route:'plant', tool_select:'workstation', defect_detective:'quality',
    safety_spot:'safety', quality_gate:'quality', logistics_route:'logistics', kanban:'logistics',
    bom_builder:'engineering', spec_check:'quality', rapid_recall:'assembly', memory_pairs:'warehouse',
    odd_one_out:'workstation', dialogue_choice:'meeting', shift_incident:'control'
  });

  const CONTEXTS = Object.freeze({
    match: {
      training:'Предсерийная сборка: сопоставьте термин с точным значением до начала инструктажа оператора.',
      shift:'Смена уже идёт: мастер уточняет термин перед передачей задания на соседний пост.',
      expert:'Изменение рабочей инструкции: выберите точное значение без риска двусмысленности для производства.'
    },
    listening: {
      training:'Тихий учебный пост: распознайте термин из короткой производственной команды.',
      shift:'Вызов по рации с линии: шум оборудования выше обычного, но термин нужно распознать сразу.',
      expert:'Короткое сообщение между цехами во время остановки линии: на уточнение формулировки времени нет.'
    },
    mistake: {
      training:'Проверка словаря рабочей инструкции: найдите единственное корректное значение.',
      shift:'Перед запуском операции нужно исключить неверную трактовку термина в сменной команде.',
      expert:'Критичная формулировка для качества: ошибка в значении может привести к неверному решению по автомобилю.'
    },
    phrase: {
      training:'Соберите фразу для спокойного инструктажа сотрудника на рабочем месте.',
      shift:'Соберите фразу, которой мастер реально воспользуется во время текущей смены.',
      expert:'Соберите короткую профессиональную формулировку для эскалации проблемы между функциями.'
    },
    hotspot: {
      training:'Осмотр учебного кузова: найдите указанную наружную деталь на схеме автомобиля.',
      shift:'На линии обнаружено замечание по кузову: быстро укажите участок, который нужно проверить.',
      expert:'Предрелизный осмотр: локализуйте нужную зону автомобиля по терминологии без дополнительных подсказок.'
    },
    assembly_order: {
      training:'Восстановите базовую последовательность технологического процесса на учебном маршруте.',
      shift:'После короткой остановки линии нужно восстановить правильный порядок операций без пропуска шага.',
      expert:'Изменённый процесс запуска: соберите последовательность так, чтобы сохранить качество и прослеживаемость.'
    },
    shop_route: {
      training:'Маршрутизация термина по заводу: определите, какой цех отвечает за эту операцию или объект.',
      shift:'Межцеховой вопрос пришёл в смену: направьте его владельцу процесса без лишней переадресации.',
      expert:'Проблема затрагивает несколько функций: выберите первичный цех-владелец для быстрой эскалации.'
    },
    tool_select: {
      training:'Рабочий пост подготовлен: выберите подходящий инструмент для указанной задачи.',
      shift:'На линии нужно подтвердить параметр без остановки соседних операций: выберите правильный инструмент.',
      expert:'Отклонение требует измеримого доказательства: выберите инструмент, который даст пригодный для решения результат.'
    },
    defect_detective: {
      training:'Учебный образец дефекта: определите визуальный тип несоответствия.',
      shift:'Контроль кузова в текущей смене: классифицируйте дефект до решения PASS / REWORK / HOLD.',
      expert:'Пограничный случай на предрелизном автомобиле: тип дефекта нужен для корректной локализации причины.'
    },
    safety_spot: {
      training:'Учебный обход участка: найдите очевидный опасный фактор до начала работы.',
      shift:'Реальная смена: производство продолжается, но опасность необходимо заметить и эскалировать сразу.',
      expert:'Near miss на участке: определите ключевой риск, который должен быть устранён до возобновления операции.'
    },
    quality_gate: {
      training:'Измерение на контрольном посту: сравните факт с допустимым диапазоном.',
      shift:'Автомобиль подошёл к quality gate: примите решение по фактическому значению.',
      expert:'Пограничное измерение перед выпуском: решение должно быть однозначным и воспроизводимым.'
    },
    logistics_route: {
      training:'Учебный материальный поток: восстановите путь детали от поставки до точки использования.',
      shift:'Поставка уже на территории завода: соберите маршрут без лишнего перемещения и ожидания линии.',
      expert:'Риск дефицита на линии: восстановите поток с правильной последовательностью контроля, хранения и подачи.'
    },
    kanban: {
      training:'Супермаркет компонентов: оцените остаток относительно точки пополнения.',
      shift:'Потребление выросло в текущей смене: примите решение по сигналу Kanban до возникновения дефицита.',
      expert:'Нестабильное потребление и ограниченный буфер: выберите действие, не создавая ни дефицит, ни лишний запас.'
    },
    bom_builder: {
      training:'Учебная eBOM: привяжите компонент к правильной подсистеме автомобиля.',
      shift:'Проверка комплектации перед сборкой: определите корректную ветвь BOM для компонента.',
      expert:'Изменение конфигурации модели: неверная привязка компонента создаст ошибку в downstream-процессах.'
    },
    spec_check: {
      training:'Сравните фактическое значение с требованием спецификации.',
      shift:'Измерение получено на посту: решите, соответствует ли оно допуску.',
      expert:'Пограничный параметр с производственным риском: решение должно опираться только на спецификацию.'
    },
    rapid_recall: {
      training:'Быстрая разминка перед сменой: узнавайте рабочие термины без длинного размышления.',
      shift:'Andon-вызов: термин нужно распознать быстро, чтобы не задерживать реакцию команды.',
      expert:'Критичное сообщение на линии: используйте мгновенное профессиональное распознавание без перевода в голове.'
    },
    memory_pairs: {
      training:'Учебный стеллаж: закрепите связь между термином и его рабочим значением.',
      shift:'Смешанная номенклатура на участке: быстро восстановите правильную терминологическую пару.',
      expert:'Передача смены по нескольким моделям: удерживайте точные соответствия без опоры на подсказки.'
    },
    odd_one_out: {
      training:'Разделите близкие производственные термины и найдите элемент другой группы.',
      shift:'В рабочем перечне оказался термин из другого процесса: найдите его до выпуска инструкции.',
      expert:'Смешанный технический список: выделите концептуально чужой термин, а не просто похожее слово.'
    },
    dialogue_choice: {
      training:'Разговор с коллегой или поставщиком: выберите профессиональную и понятную реплику.',
      shift:'Реальная рабочая коммуникация: нужен ответ, который двигает проблему к containment и следующему действию.',
      expert:'Эскалация между функциями: выберите формулировку с владельцем, сроком, доказательством и понятным следующим шагом.'
    },
    shift_incident: {
      training:'Разберите учебный инцидент и выберите безопасное первое действие.',
      shift:'Событие происходит прямо сейчас: выберите действие, которое защищает качество, людей и непрерывность процесса.',
      expert:'Несколько рисков одновременно: приоритизируйте containment и управляемую эскалацию до поиска корневой причины.'
    }
  });

  let installed = false;
  let observer = null;
  let scheduled = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }

  function storedDifficulty() {
    const snapshot = current();
    const stateValue = snapshot.gameDepthDifficulty;
    if (LEVELS[stateValue]) return stateValue;
    try {
      const saved = root.localStorage && root.localStorage.getItem(STORAGE_KEY);
      if (LEVELS[saved]) return saved;
    } catch (_) {}
    return 'adaptive';
  }

  function setDifficulty(value) {
    const next = LEVELS[value] ? value : 'adaptive';
    try { if (root.localStorage) root.localStorage.setItem(STORAGE_KEY, next); } catch (_) {}
    state().set('gameDepthDifficulty', next);
    decorate();
    return next;
  }

  function effectiveDifficulty(index) {
    const selected = storedDifficulty();
    if (selected !== 'adaptive') return selected;
    if (Number(index || 0) <= 1) return 'training';
    if (Number(index || 0) <= 3) return 'shift';
    return 'expert';
  }

  function detectScene(gameType, item) {
    const type = String(gameType || '');
    const visual = String((item && item.visual) || '').toLowerCase();
    const text = [item && item.prompt, item && item.translation, item && item.term, item && item.target].filter(Boolean).join(' ').toLowerCase();

    if (type === 'defect_detective') {
      if (['orange-peel','paint-run','pinhole'].indexOf(visual) !== -1) return 'paint';
      if (visual === 'weld-spatter') return 'welding';
      if (visual === 'gap' || visual === 'flush') return 'body';
      return 'quality';
    }
    if (type === 'shop_route') {
      if (text.indexOf('paint') !== -1 || text.indexOf('окра') !== -1) return 'paint';
      if (text.indexOf('weld') !== -1 || text.indexOf('свар') !== -1) return 'welding';
      if (text.indexOf('logist') !== -1 || text.indexOf('логист') !== -1) return 'logistics';
    }
    if (type === 'tool_select') {
      if (text.indexOf('spray') !== -1 || text.indexOf('coating') !== -1 || text.indexOf('окра') !== -1) return 'paint';
      if (text.indexOf('forklift') !== -1 || text.indexOf('barcode') !== -1 || text.indexOf('логист') !== -1) return 'logistics';
    }
    if (type === 'assembly_order') {
      if (text.indexOf('paint') !== -1 || text.indexOf('degrease') !== -1 || text.indexOf('primer') !== -1 || text.indexOf('окра') !== -1) return 'paint';
      if (text.indexOf('incoming') !== -1 || text.indexOf('warehouse') !== -1 || text.indexOf('постав') !== -1) return 'logistics';
    }
    if (type === 'dialogue_choice' || type === 'shift_incident') {
      if (text.indexOf('paint') !== -1 || text.indexOf('окра') !== -1 || text.indexOf('particle') !== -1) return 'paint';
      if (text.indexOf('supplier') !== -1 || text.indexOf('постав') !== -1 || text.indexOf('freight') !== -1 || text.indexOf('customs') !== -1) return 'logistics';
      if (text.indexOf('weld') !== -1 || text.indexOf('свар') !== -1) return 'welding';
      if (text.indexOf('torque') !== -1 || text.indexOf('момент') !== -1 || text.indexOf('defect') !== -1 || text.indexOf('дефект') !== -1) return 'quality';
    }
    return GAME_SCENES[type] || 'assembly';
  }

  function sceneTitle(scene) {
    return ({
      vehicle:'Кузов автомобиля', body:'Кузовной контроль', welding:'Сварочный цех', paint:'Окрасочная камера',
      logistics:'Логистический док', quality:'Контроль качества', assembly:'Сборочная линия', plant:'Маршрут по заводу',
      workstation:'Рабочий пост', safety:'Безопасность участка', engineering:'Инженерный стол', warehouse:'Склад компонентов',
      meeting:'Рабочая коммуникация', control:'Сменный control room'
    })[scene] || 'Производственная сцена';
  }

  function levelMeta(level) {
    return LEVELS[level] || LEVELS.training;
  }

  function constraintsFor(level, scene) {
    if (level === 'training') return ['Контекст: полный', 'Подсказки: включены', 'Фокус: точность'];
    if (level === 'shift') return ['Контекст: рабочий', 'Подсказки: минимум', scene === 'logistics' ? 'Фокус: поток' : 'Фокус: решение'];
    return ['Контекст: критичный', 'Подсказки: скрыты', scene === 'quality' ? 'Фокус: доказательство' : 'Фокус: приоритет'];
  }

  function sceneMarkup(scene) {
    if (scene === 'paint') {
      return '<div class="v621-visual v621-paint"><span class="v621-booth-wall left"></span><span class="v621-booth-wall right"></span>' +
        '<div class="v621-body-shell"><i></i><b></b></div><div class="v621-paint-robot r1"><i></i><b></b></div>' +
        '<div class="v621-paint-robot r2"><i></i><b></b></div><div class="v621-airflow"><i></i><i></i><i></i></div>' +
        '<span class="v621-scene-label">PAINT BOOTH · BODY SURFACE · PROCESS CONTROL</span></div>';
    }
    if (scene === 'welding') {
      return '<div class="v621-visual v621-welding"><div class="v621-weld-body"><i></i><b></b><em></em></div>' +
        '<div class="v621-weld-robot left"><i></i><b></b></div><div class="v621-weld-robot right"><i></i><b></b></div>' +
        '<div class="v621-sparks"><i></i><i></i><i></i><i></i><i></i></div><span class="v621-scene-label">BODY SHOP · SPOT WELD · GEOMETRY</span></div>';
    }
    if (scene === 'logistics') {
      return '<div class="v621-visual v621-logistics"><div class="v621-dock"><i>DOCK 04</i><b></b></div>' +
        '<div class="v621-truck"><i></i><b></b><em></em></div><div class="v621-pallet p1"><i></i><i></i></div>' +
        '<div class="v621-pallet p2"><i></i><i></i></div><div class="v621-forklift"><i></i><b></b></div>' +
        '<span class="v621-route-line"></span><span class="v621-scene-label">RECEIVING · SUPERMARKET · LINE FEEDING</span></div>';
    }
    if (scene === 'quality' || scene === 'body') {
      return '<div class="v621-visual v621-quality"><div class="v621-q-body"><i></i><b></b></div><span class="v621-scan s1"></span>' +
        '<span class="v621-scan s2"></span><div class="v621-measure-card"><span>SPEC</span><b>±</b><i>TRACE</i></div>' +
        '<div class="v621-light-tunnel"><i></i><i></i><i></i></div><span class="v621-scene-label">QUALITY GATE · MEASUREMENT · TRACEABILITY</span></div>';
    }
    if (scene === 'safety') {
      return '<div class="v621-visual v621-safety"><div class="v621-safe-machine"><span>LOCKOUT</span></div>' +
        '<div class="v621-safe-worker"><i></i><b></b></div><div class="v621-safe-forklift"><i></i><b></b></div>' +
        '<span class="v621-walkway"></span><span class="v621-hazard">!</span><span class="v621-scene-label">PPE · WALKWAY · LOTO · NEAR MISS</span></div>';
    }
    if (scene === 'meeting' || scene === 'control') {
      return '<div class="v621-visual v621-meeting"><div class="v621-screen"><span>ISSUE</span><b>OWNER</b><i>DUE</i></div>' +
        '<div class="v621-person p1"><i></i><b></b></div><div class="v621-person p2"><i></i><b></b></div>' +
        '<div class="v621-person p3"><i></i><b></b></div><span class="v621-talk-line"></span><span class="v621-scene-label">FACTS · OWNER · ACTION · EVIDENCE</span></div>';
    }
    if (scene === 'engineering') {
      return '<div class="v621-visual v621-engineering"><div class="v621-cad"><span>VEHICLE</span><i>BODY</i><i>CHASSIS</i><i>ELEC</i></div>' +
        '<div class="v621-bom"><span>EBOM</span><b>01</b><b>02</b><b>03</b></div><div class="v621-change">ECN</div>' +
        '<span class="v621-scene-label">BOM · VARIANT · CHANGE CONTROL</span></div>';
    }
    if (scene === 'warehouse' || scene === 'workstation') {
      return '<div class="v621-visual v621-workstation"><div class="v621-rack"><i>A01</i><i>A02</i><i>B01</i><i>B02</i></div>' +
        '<div class="v621-bench"><span>TOOL</span><b>GAUGE</b><i>PART</i></div><div class="v621-screen-small">WI</div>' +
        '<span class="v621-scene-label">PART · TOOL · STANDARD WORK</span></div>';
    }
    if (scene === 'plant') {
      return '<div class="v621-visual v621-plant"><span>STAMPING</span><b>→</b><span>WELDING</span><b>→</b><span>PAINT</span><b>→</b>' +
        '<span>ASSEMBLY</span><b>→</b><span>QUALITY</span><b>→</b><span>LOGISTICS</span></div>';
    }
    if (scene === 'vehicle') return '';
    return '<div class="v621-visual v621-assembly"><div class="v621-conveyor"></div><div class="v621-line-car"><i></i><b></b></div>' +
      '<div class="v621-station s1">ST 120</div><div class="v621-station s2">ST 130</div><div class="v621-andon">ANDON</div>' +
      '<span class="v621-scene-label">ASSEMBLY LINE · STANDARD WORK · QUALITY</span></div>';
  }

  function contextMarkup(gameType, item, level, scene) {
    const meta = levelMeta(level);
    const context = (CONTEXTS[gameType] && CONTEXTS[gameType][level]) || 'Решите задачу в контексте реального автомобильного производства.';
    const constraints = constraintsFor(level, scene);
    return '<div class="v621-context"><div class="v621-context-head"><span>' + esc(sceneTitle(scene)) + '</span>' +
      '<b class="v621-level level-' + esc(level) + '">Уровень ' + esc(meta.short) + ' · ' + esc(meta.label) + '</b></div>' +
      '<p>' + esc(context) + '</p><div class="v621-constraints">' + constraints.map(function (value) {
        return '<span>' + esc(value) + '</span>';
      }).join('') + '</div></div>';
  }

  function enhanceCar(level) {
    const stage = query('.car-hotspot-stage');
    const svg = stage && query('svg', stage);
    if (!stage || !svg || svg.dataset.v621Detailed === '1') return;
    svg.dataset.v621Detailed = '1';
    stage.classList.add('v621-detailed-car', 'v621-' + level);
    svg.insertAdjacentHTML('beforeend',
      '<g class="v621-car-details" aria-hidden="true">' +
      '<path class="v621-roof-line" d="M252 162 L285 108 L448 108 Q490 112 535 160"/>' +
      '<path class="v621-belt-line" d="M155 166 C275 165 510 165 651 188"/>' +
      '<path class="v621-rocker" d="M265 238 L526 238"/>' +
      '<path class="v621-hood-seam" d="M530 161 L621 178"/>' +
      '<path class="v621-fender-line" d="M618 194 Q650 210 646 238"/>' +
      '<rect class="v621-handle" x="445" y="184" width="31" height="7" rx="3"/>' +
      '<rect class="v621-handle" x="330" y="184" width="27" height="7" rx="3"/>' +
      '<path class="v621-grille" d="M669 207 L701 214 L696 235 L664 235 Z"/>' +
      '<path class="v621-lamp" d="M636 177 Q676 178 687 195 L650 200 Z"/>' +
      '<path class="v621-tail" d="M112 184 L145 175 L151 207 L118 211 Z"/>' +
      '<circle class="v621-hub" cx="210" cy="248" r="21"/><circle class="v621-hub" cx="580" cy="248" r="21"/>' +
      '<path class="v621-wheel-spoke" d="M210 229 V267 M191 248 H229 M196 234 L224 262 M224 234 L196 262"/>' +
      '<path class="v621-wheel-spoke" d="M580 229 V267 M561 248 H599 M566 234 L594 262 M594 234 L566 262"/>' +
      '<path class="v621-pillar" d="M331 108 L317 160 M448 108 L468 160"/>' +
      '</g>');
    stage.insertAdjacentHTML('beforeend', '<div class="v621-car-subsystems"><span>Кузов</span><span>Остекление</span><span>Светотехника</span><span>Колёса</span></div>');
  }

  function decorateCatalog() {
    const summary = query('.game-lab-summary');
    if (!summary) return false;
    let panel = query('.v621-difficulty-panel');
    if (!panel) {
      summary.insertAdjacentHTML('afterend',
        '<section class="v621-difficulty-panel"><div><span class="kicker">PRODUCTION DIFFICULTY</span><h2>Режим сложности</h2>' +
        '<p>В адаптивном режиме 5 вопросов проходят путь от обучения к реальной смене и экспертному решению.</p></div>' +
        '<div class="v621-level-buttons">' + Object.keys(LEVELS).map(function (key) {
          return '<button type="button" data-v621-difficulty="' + key + '"><b>' + esc(LEVELS[key].label) + '</b><small>' + esc(LEVELS[key].caption) + '</small></button>';
        }).join('') + '</div></section>');
      panel = query('.v621-difficulty-panel');
      queryAll('[data-v621-difficulty]', panel).forEach(function (button) {
        button.addEventListener('click', function () { setDifficulty(button.dataset.v621Difficulty); });
      });
    }
    const selected = storedDifficulty();
    queryAll('[data-v621-difficulty]', panel).forEach(function (button) {
      button.classList.toggle('active', button.dataset.v621Difficulty === selected);
    });

    queryAll('.game-lab-card').forEach(function (card) {
      if (query('.v621-card-depth', card)) return;
      const gameType = card.dataset.startV618Game || '';
      const scene = GAME_SCENES[gameType] || 'assembly';
      const copy = query('.game-lab-copy', card);
      if (copy) copy.insertAdjacentHTML('beforeend', '<span class="v621-card-depth">3 уровня · ' + esc(sceneTitle(scene)) + '</span>');
    });
    return true;
  }

  function decorateSession() {
    const shell = query('.game-session-shell');
    if (!shell) return false;
    const snapshot = current();
    const session = snapshot.gameSessionV618;
    if (!session || !Array.isArray(session.items)) return false;
    const index = Number(snapshot.gameIndexV618 || 0);
    const item = session.items[index];
    if (!item) return false;
    const level = effectiveDifficulty(index);
    const scene = detectScene(session.game_type, item);
    const key = String(session.session_id || session.game_type) + ':' + index + ':' + level;
    if (shell.dataset.v621DepthKey === key) return true;
    shell.dataset.v621DepthKey = key;
    shell.classList.add('v621-depth', 'v621-level-' + level, 'v621-scene-' + scene);

    const top = query('.game-session-top', shell);
    if (top && !query('.v621-top-badge', top)) {
      top.insertAdjacentHTML('beforeend', '<span class="v621-top-badge level-' + esc(level) + '">' + esc(levelMeta(level).label) + '</span>');
    }

    const stage = query('.game-stage', shell);
    if (!stage) return true;
    stage.classList.add('v621-enriched');
    stage.insertAdjacentHTML('afterbegin', contextMarkup(session.game_type, item, level, scene));
    const visual = sceneMarkup(scene);
    if (visual) query('.v621-context', stage).insertAdjacentHTML('afterend', visual);
    if (scene === 'vehicle') enhanceCar(level);
    return true;
  }

  function decorate() {
    scheduled = false;
    if (String(current().view || '') !== 'games') return;
    decorateCatalog();
    decorateSession();
  }

  function scheduleDecorate() {
    if (scheduled) return;
    scheduled = true;
    root.requestAnimationFrame ? root.requestAnimationFrame(decorate) : root.setTimeout(decorate, 0);
  }

  function install() {
    if (installed) return;
    installed = true;
    const main = query('#main');
    if (main && root.MutationObserver) {
      observer = new MutationObserver(scheduleDecorate);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener('mgc:state-change', function (event) {
      const detail = event && event.detail ? event.detail : {};
      if (detail.key === 'view' || detail.key === 'gameDepthDifficulty' || detail.key === 'gameIndexV618' || detail.patch) scheduleDecorate();
    });
    document.addEventListener('mgc:frontend-ready', scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register('game-depth-v621', {
    levels:LEVELS,
    scenes:GAME_SCENES,
    contexts:CONTEXTS,
    getDifficulty:storedDifficulty,
    setDifficulty:setDifficulty,
    effectiveDifficulty:effectiveDifficulty,
    detectScene:detectScene,
    decorate:decorate,
    install:install
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
