/* v6.0.30 Stage C — final Game World polish. Visual/context only. */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const STAGE_C = Object.freeze({
    match:{brief:'Сопоставьте термин с точным рабочим значением.',hint:'Смотрите на смысл термина, а не на похожее слово.'},
    listening:{brief:'Распознайте термин на слух и выберите значение.',hint:'Сначала слушайте целиком, затем ориентируйтесь на ключевой звук.'},
    mistake:{brief:'Найдите единственную профессионально точную формулировку.',hint:'В производстве похожие слова могут означать разные действия.'},
    phrase:{brief:'Соберите рабочую фразу в правильном порядке.',hint:'Сначала определите действие, затем объект и уточнение.'},
    hotspot:{brief:'Найдите нужную деталь прямо на автомобиле.',hint:'Используйте расположение узла как визуальную подсказку.'},
    assembly_order:{brief:'Восстановите технологическую последовательность.',hint:'Думайте как о реальном движении автомобиля по производству.'},
    shop_route:{brief:'Направьте термин в правильный цех.',hint:'Свяжите термин с операцией, а операцию — с зоной завода.'},
    tool_select:{brief:'Выберите инструмент под производственную задачу.',hint:'Сопоставьте действие, измерение и назначение инструмента.'},
    defect_detective:{brief:'Опознайте дефект по производственному контексту.',hint:'Сначала определите поверхность или процесс, затем тип дефекта.'},
    safety_spot:{brief:'Найдите риск и выберите безопасное действие.',hint:'Приоритет — остановить опасность, затем восстановить безопасные условия.'},
    quality_gate:{brief:'Примите решение PASS / REWORK / HOLD по измерению.',hint:'Сравните факт с допустимым диапазоном до выбора статуса.'},
    logistics_route:{brief:'Соберите правильный материальный поток.',hint:'Следите за логикой Dock → Supermarket → Line side.'},
    kanban:{brief:'Примите решение о пополнении по сигналу Kanban.',hint:'Сравните остаток с точкой заказа.'},
    bom_builder:{brief:'Привяжите компонент к правильной подсистеме BOM.',hint:'Думайте по структуре Vehicle → System → Component.'},
    spec_check:{brief:'Определите, находится ли факт внутри допуска.',hint:'Проверяйте обе границы диапазона, не только номинал.'},
    rapid_recall:{brief:'Дайте точный ответ в ограниченное время.',hint:'Не переводите всю фразу — ищите ключевой производственный термин.'},
    memory_pairs:{brief:'Найдите правильную пару для термина.',hint:'Запоминайте смысл и позицию карточек одновременно.'},
    odd_one_out:{brief:'Найдите термин из другой функциональной группы.',hint:'Сначала определите общий инженерный признак трёх элементов.'},
    dialogue_choice:{brief:'Выберите профессиональную реплику в рабочем диалоге.',hint:'Лучший ответ должен давать действие, факт или следующий шаг.'},
    shift_incident:{brief:'Примите решение в сменной производственной ситуации.',hint:'Сначала безопасность и containment, затем анализ и восстановление.'}
  });

  const seenSessions = new Set();
  let busy = false;
  let queued = false;
  let lastSessionKey = '';
  let lastIndex = -1;
  let noticeTimer = null;

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
  function sessionInfo() {
    const s = snapshot();
    const modern = s.gameSessionV618 || null;
    const legacy = s.gameSession || null;
    const session = modern || legacy;
    if (!session || !session.game_type) return null;
    return {
      session:session,
      type:String(session.game_type),
      index:Number(modern ? (s.gameIndexV618 || 0) : (s.gameIndex || 0)),
      total:Array.isArray(session.items) ? session.items.length : 5,
      key:String(session.session_id || session.id || session.game_type)
    };
  }
  function gameShell() {
    return main.querySelector('.game-session-shell,.quiz-stage');
  }
  function isResult() {
    return Boolean(main.querySelector('.game-result-panel,.exam-intro .result-score'));
  }
  function railHTML(index,total) {
    const safeTotal = Math.max(1,Math.min(5,Number(total || 5)));
    let dots = '';
    for (let i=0;i<safeTotal;i+=1) {
      const state = i < index ? 'done' : i === index ? 'active' : 'next';
      dots += '<i class="gw30c-step ' + state + '"><span>' + (i+1) + '</span></i>';
    }
    return '<div class="gw30c-rail" aria-label="Прогресс миссии"><div class="gw30c-rail-copy"><small>MISSION FLOW</small><b>Операция ' +
      Math.min(index+1,safeTotal) + ' / ' + safeTotal + '</b></div><div class="gw30c-steps">' + dots + '</div></div>';
  }
  function onboardingHTML(info) {
    const copy = STAGE_C[info.type] || {brief:'Выполните пять коротких производственных заданий.',hint:'Точность важнее скорости.'};
    return '<div class="gw30c-onboarding" role="dialog" aria-modal="true" aria-label="Инструктаж перед игровой миссией">' +
      '<div class="gw30c-onboarding-card"><div class="gw30c-brief-mark"><span></span><small>MISSION BRIEFING</small></div>' +
      '<h2>' + esc(copy.brief) + '</h2><p>' + esc(copy.hint) + '</p>' +
      '<div class="gw30c-brief-meta"><span><b>5</b> операций</span><span><b>1</b> короткая сессия</span><span><b>XP</b> считает сервер</span></div>' +
      '<button class="primary wide" data-gw30c-start>Начать миссию</button></div></div>';
  }
  function addOnboarding(info) {
    if (!gameShell() || seenSessions.has(info.key) || main.querySelector('.gw30c-onboarding')) return;
    seenSessions.add(info.key);
    main.insertAdjacentHTML('beforeend',onboardingHTML(info));
    const start = main.querySelector('[data-gw30c-start]');
    if (start) start.addEventListener('click',function () {
      const overlay = main.querySelector('.gw30c-onboarding');
      if (overlay) {
        overlay.classList.add('leaving');
        root.setTimeout(function () { if (overlay.parentNode) overlay.remove(); },220);
      }
      const first = main.querySelector('[data-v618-choice],[data-hotspot-zone],[data-order-token],[data-game-answer],#playGameAudio');
      if (first && first.focus) root.setTimeout(function () { first.focus(); },240);
    });
  }
  function addRail(info) {
    const shell = gameShell();
    if (!shell) return;
    const old = shell.querySelector('.gw30c-rail');
    if (old) old.remove();
    const top = shell.querySelector('.game-session-top,.quiz-progress');
    if (top) top.insertAdjacentHTML('afterend',railHTML(info.index,info.total));
    else shell.insertAdjacentHTML('afterbegin',railHTML(info.index,info.total));
  }
  function showRecordedNotice(info) {
    const shell = gameShell();
    if (!shell || info.index <= 0 || info.index >= info.total) return;
    const old = main.querySelector('.gw30c-recorded');
    if (old) old.remove();
    const notice = root.document.createElement('div');
    notice.className = 'gw30c-recorded';
    notice.setAttribute('role','status');
    notice.setAttribute('aria-live','polite');
    notice.innerHTML = '<span>✓</span><div><b>Ответ зафиксирован</b><small>Переходим к операции ' + (info.index + 1) + ' из ' + info.total + '</small></div>';
    shell.insertBefore(notice,shell.firstChild);
    if (noticeTimer) root.clearTimeout(noticeTimer);
    noticeTimer = root.setTimeout(function () {
      notice.classList.add('leaving');
      root.setTimeout(function () { if (notice.parentNode) notice.remove(); },180);
    },1150);
  }
  function decorateResult() {
    const panel = main.querySelector('.game-result-panel,.exam-intro');
    if (!panel || panel.querySelector('.gw30c-result-hero')) return;
    const scoreNode = panel.querySelector('.game-result-score,.result-score');
    const text = scoreNode ? scoreNode.textContent : '0/5';
    const values = text.match(/(\d+)\s*\/\s*(\d+)/);
    const score = values ? Number(values[1]) : 0;
    const total = values ? Math.max(1,Number(values[2])) : 5;
    const ratio = score / total;
    const tier = ratio === 1 ? 'perfect' : ratio >= .6 ? 'strong' : 'developing';
    const title = tier === 'perfect' ? 'Миссия выполнена без ошибок' : tier === 'strong' ? 'Миссия выполнена' : 'Миссия завершена';
    const note = tier === 'perfect' ? 'Производственная коммуникация — точный проход.' : tier === 'strong' ? 'Хорошая база. Следующая попытка закрепит слабые места.' : 'Результат сохранён. Повторите механику позже с новой выборкой.';
    const hero = root.document.createElement('div');
    hero.className = 'gw30c-result-hero ' + tier;
    hero.innerHTML = '<div class="gw30c-result-ring"><span>' + score + '</span><small>/' + total + '</small></div>' +
      '<div><small>MISSION COMPLETE</small><h2>' + esc(title) + '</h2><p>' + esc(note) + '</p></div>' +
      '<div class="gw30c-burst" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
    panel.insertBefore(hero,panel.firstChild);
    main.classList.add('gw30c-result-state');
  }
  function markPressed(event) {
    const target = event.target && event.target.closest ? event.target.closest('[data-v618-choice],[data-hotspot-zone],[data-order-done],[data-game-answer],#phraseDone') : null;
    if (!target || target.disabled) return;
    target.classList.add('gw30c-pressed');
  }
  function cleanupResultState() {
    if (!isResult()) main.classList.remove('gw30c-result-state');
  }
  function decorate() {
    if (busy) return;
    busy = true;
    try {
      cleanupResultState();
      const info = sessionInfo();
      if (!info) {
        lastSessionKey = '';
        lastIndex = -1;
        if (isResult()) decorateResult();
        return;
      }
      main.classList.add('gw30c-active');
      addRail(info);
      addOnboarding(info);
      if (info.key === lastSessionKey && lastIndex >= 0 && info.index > lastIndex) showRecordedNotice(info);
      lastSessionKey = info.key;
      lastIndex = info.index;
    } finally { busy = false; }
  }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; decorate(); });
  }

  new MutationObserver(schedule).observe(main,{childList:true,subtree:true});
  root.document.addEventListener('click',markPressed,true);
  root.document.addEventListener('click',function (event) {
    if (event.target && event.target.closest && event.target.closest('[data-view="games"],[data-start-v618-game],[data-start-game],[data-replay-v618],[data-go-games-home],[data-go="games"]')) {
      root.setTimeout(schedule,0);
    }
  });
  root.addEventListener('popstate',schedule);
  schedule();
})(window);
