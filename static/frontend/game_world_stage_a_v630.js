/* v6.0.30 Stage A — production-depth visual context. No scoring/API/XP behavior lives here. */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const STAGE_A = Object.freeze({
    match: {scene:'assembly', label:'Сборка', mode:'Термины на линии'},
    listening: {scene:'assembly', label:'Сборка', mode:'Команда оператора'},
    phrase: {scene:'assembly', label:'Сборка', mode:'Рабочая фраза'},
    hotspot: {scene:'assembly', label:'Сборка', mode:'Детали автомобиля'},
    assembly_order: {scene:'assembly', label:'Сборка', mode:'Порядок операций'},
    tool_select: {scene:'assembly', label:'Сборка', mode:'Выбор инструмента'},
    safety_spot: {scene:'welding', label:'Сварка', mode:'Безопасная зона'},
    shift_incident: {scene:'welding', label:'Сварка', mode:'Инцидент смены'},
    defect_detective: {scene:'paint', label:'Окраска', mode:'Поиск дефекта'},
    shop_route: {scene:'logistics', label:'Логистика', mode:'Маршрут по заводу'},
    logistics_route: {scene:'logistics', label:'Логистика', mode:'Материальный поток'},
    kanban: {scene:'logistics', label:'Логистика', mode:'Пополнение линии'}
  });

  let queued = false;
  let engagingTimer = null;

  function frontend() { return root.MGCFrontend || null; }
  function snapshot() {
    try {
      const f = frontend();
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }

  function activeType() {
    const state = snapshot();
    if (state.gameSessionV618 && state.gameSessionV618.game_type) return String(state.gameSessionV618.game_type);
    if (state.gameSession && state.gameSession.game_type) return String(state.gameSession.game_type);
    const session = main.querySelector('.game-lab-session[data-game-type]');
    return session ? String(session.dataset.gameType || '') : '';
  }

  function sceneAssembly() {
    return '<section class="gw30a-production-scene gw30a-assembly" aria-label="Сцена сборочного цеха">' +
      '<div class="gw30a-scene-copy"><small>ASSEMBLY LINE · LIVE</small><b>Автомобиль движется по операциям сборки</b><span>Определите термин, деталь, инструмент или правильную последовательность.</span></div>' +
      '<div class="gw30a-assembly-line" aria-hidden="true"><div class="gw30a-mini-car"><i></i><b></b></div>' +
      '<div class="gw30a-op active"><i>01</i><span>Body</span></div><em></em><div class="gw30a-op"><i>02</i><span>Trim</span></div><em></em>' +
      '<div class="gw30a-op"><i>03</i><span>Chassis</span></div><em></em><div class="gw30a-op"><i>04</i><span>Final</span></div></div>' +
      '<div class="gw30a-status"><span><i></i> LINE RUNNING</span><b> takt 60 s</b></div></section>';
  }

  function sceneWelding() {
    return '<section class="gw30a-production-scene gw30a-welding" aria-label="Сцена сварочного цеха">' +
      '<div class="gw30a-scene-copy"><small>BODY SHOP · ROBOT CELL</small><b>Контроль операции в сварочной ячейке</b><span>Следите за безопасностью, терминологией и решением сменной ситуации.</span></div>' +
      '<div class="gw30a-weld-cell" aria-hidden="true"><div class="gw30a-biw"><i></i><i></i><i></i><i></i><i></i><i></i></div>' +
      '<div class="gw30a-weld-arm left"><i></i><b></b></div><div class="gw30a-weld-arm right"><i></i><b></b></div>' +
      '<span class="gw30a-spark s1"></span><span class="gw30a-spark s2"></span><span class="gw30a-spark s3"></span></div>' +
      '<div class="gw30a-status"><span><i></i> CELL SAFE</span><b>BIW / spot welding</b></div></section>';
  }

  function scenePaint() {
    return '<section class="gw30a-production-scene gw30a-paint" aria-label="Сцена окрасочного цеха">' +
      '<div class="gw30a-scene-copy"><small>PAINT SHOP · INSPECTION</small><b>Визуальный контроль поверхности кузова</b><span>Сопоставьте рабочий термин с реальным типом дефекта покрытия.</span></div>' +
      '<div class="gw30a-paint-panel" aria-hidden="true"><div class="gw30a-paint-scan"></div><div class="gw30a-panel-shape"></div>' +
      '<span class="gw30a-defect scratch"><i></i><b>scratch</b></span><span class="gw30a-defect run"><i></i><b>paint run</b></span>' +
      '<span class="gw30a-defect peel"><i></i><b>orange peel</b></span></div>' +
      '<div class="gw30a-status"><span><i></i> INSPECTION ACTIVE</span><b>surface quality</b></div></section>';
  }

  function sceneLogistics() {
    return '<section class="gw30a-production-scene gw30a-logistics" aria-label="Сцена внутризаводской логистики">' +
      '<div class="gw30a-scene-copy"><small>INTRALOGISTICS · MATERIAL FLOW</small><b>Доставка компонента к точке потребления</b><span>Определите маршрут, решение Kanban или правильную производственную зону.</span></div>' +
      '<div class="gw30a-flow-map" aria-hidden="true"><div class="gw30a-route-line"></div>' +
      '<div class="gw30a-flow-node dock"><i>01</i><b>Dock</b></div><div class="gw30a-flow-node market"><i>02</i><b>Supermarket</b></div>' +
      '<div class="gw30a-flow-node line"><i>03</i><b>Line side</b></div><div class="gw30a-tugger"><i></i><b></b></div>' +
      '<span class="gw30a-box box-a"></span><span class="gw30a-box box-b"></span></div>' +
      '<div class="gw30a-status"><span><i></i> FLOW SYNCHRONIZED</span><b>FIFO · Kanban</b></div></section>';
  }

  function sceneHTML(world) {
    if (!world) return '';
    if (world.scene === 'welding') return sceneWelding();
    if (world.scene === 'paint') return scenePaint();
    if (world.scene === 'logistics') return sceneLogistics();
    return sceneAssembly();
  }

  function decorateExistingMechanic(type, world) {
    const stage = main.querySelector('.game-stage');
    if (!stage) return;
    stage.dataset.productionScene = world.scene;
    stage.dataset.productionGame = type;

    const hotspot = stage.querySelector('.car-hotspot-stage');
    if (hotspot) hotspot.classList.add('gw30a-hotspot-enhanced');
    const order = stage.querySelector('.order-track');
    if (order) order.classList.add('gw30a-order-enhanced');
    const tools = stage.querySelector('.tool-rack');
    if (tools) tools.classList.add('gw30a-tools-enhanced');
    const defect = stage.querySelector('.defect-visual');
    if (defect) defect.classList.add('gw30a-defect-enhanced');
    const safety = stage.querySelector('.safety-visual');
    if (safety) safety.classList.add('gw30a-safety-enhanced');
    const route = stage.querySelector('.factory-route');
    if (route) route.classList.add('gw30a-route-enhanced');
    const kanban = stage.querySelector('.kanban-board');
    if (kanban) kanban.classList.add('gw30a-kanban-enhanced');
  }

  function cleanup() {
    main.classList.remove('gw30a-enabled','gw30a-engaged');
    main.removeAttribute('data-gw30a-scene');
    main.removeAttribute('data-gw30a-game');
    main.querySelectorAll('.gw30a-production-scene').forEach(function (node) { node.remove(); });
  }

  function decorate() {
    const type = activeType();
    const world = STAGE_A[type];
    if (!world || !main.querySelector('.game-session-shell,.game-lab-session')) {
      cleanup();
      return;
    }

    main.classList.add('gw30a-enabled');
    main.dataset.gw30aScene = world.scene;
    main.dataset.gw30aGame = type;

    const shell = main.querySelector('.game-session-shell,.game-lab-session');
    if (shell && !shell.querySelector('.gw30a-production-scene')) {
      const top = shell.querySelector('.game-session-top');
      if (top) top.insertAdjacentHTML('afterend', sceneHTML(world));
      else shell.insertAdjacentHTML('afterbegin', sceneHTML(world));
    }
    decorateExistingMechanic(type, world);
  }

  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () {
      queued = false;
      decorate();
    });
  }

  function engage(event) {
    if (!main.classList.contains('gw30a-enabled')) return;
    if (!event.target || !event.target.closest) return;
    if (!event.target.closest('[data-v618-choice],[data-hotspot-zone],[data-order-token],[data-order-done],[data-play-v618-audio]')) return;
    main.classList.add('gw30a-engaged');
    if (engagingTimer) root.clearTimeout(engagingTimer);
    engagingTimer = root.setTimeout(function () { main.classList.remove('gw30a-engaged'); }, 420);
  }

  new MutationObserver(schedule).observe(main, {childList:true, subtree:true});
  root.document.addEventListener('click', engage, true);
  root.addEventListener('popstate', schedule);
  schedule();
})(window);
