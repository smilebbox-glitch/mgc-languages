/* v6.0.30 Stage B — Quality + Engineering visual context. No scoring/API/XP behavior lives here. */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const STAGE_B = Object.freeze({
    mistake: {scene:'quality', label:'Качество', mode:'Precision Check'},
    quality_gate: {scene:'quality', label:'Качество', mode:'PASS / REWORK / HOLD'},
    spec_check: {scene:'quality', label:'Качество', mode:'Допуск и измерение'},
    bom_builder: {scene:'engineering', label:'Инженерия', mode:'BOM / subsystem'},
    odd_one_out: {scene:'engineering', label:'Инженерия', mode:'Классификация терминов'}
  });

  let queued = false;
  let pulseTimer = null;

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

  function qualityScene(type) {
    const mode = type === 'quality_gate' ? 'QUALITY GATE' : (type === 'spec_check' ? 'SPEC CHECK' : 'PRECISION');
    return '<section class="gw30b-production-scene gw30b-quality" aria-label="Пост контроля качества">' +
      '<div class="gw30b-scene-copy"><small>QUALITY LAB · ' + mode + '</small><b>Измерение, допуск и решение по детали</b>' +
      '<span>Сопоставьте рабочий термин с результатом контроля и правильным статусом детали.</span></div>' +
      '<div class="gw30b-quality-cell" aria-hidden="true">' +
      '<div class="gw30b-cmm"><i class="axis-x"></i><i class="axis-z"></i><b class="probe"></b><span class="part"></span></div>' +
      '<div class="gw30b-measure-panel"><small>NOMINAL</small><b>25.00</b><span>± 0.20 mm</span><div class="gw30b-tolerance"><i></i><em></em></div></div>' +
      '<div class="gw30b-status-stack"><span class="pass">PASS</span><span class="rework">REWORK</span><span class="hold">HOLD</span></div>' +
      '</div><div class="gw30b-status"><span><i></i> MEASUREMENT LIVE</span><b>CMM · tolerance · disposition</b></div></section>';
  }

  function engineeringScene(type) {
    const mode = type === 'bom_builder' ? 'BOM DIGITAL THREAD' : 'ENGINEERING CLASSIFICATION';
    return '<section class="gw30b-production-scene gw30b-engineering" aria-label="Инженерная рабочая сцена">' +
      '<div class="gw30b-scene-copy"><small>ENGINEERING · ' + mode + '</small><b>От чертежа к компоненту и подсистеме</b>' +
      '<span>Свяжите термин с правильной инженерной структурой, BOM или функциональной группой.</span></div>' +
      '<div class="gw30b-engineering-board" aria-hidden="true">' +
      '<div class="gw30b-drawing"><span>A3 DRAWING</span><i class="line l1"></i><i class="line l2"></i><i class="line l3"></i><b>Ø12 H7</b><em>R0.8</em></div>' +
      '<div class="gw30b-thread"><i></i><i></i><i></i></div>' +
      '<div class="gw30b-bom-tree"><span>VEHICLE</span><b>└ BODY</b><b>  └ MODULE</b><strong>    └ COMPONENT</strong></div>' +
      '<div class="gw30b-data-card"><small>REV</small><b>C</b><span>released</span></div>' +
      '</div><div class="gw30b-status"><span><i></i> DIGITAL THREAD LINKED</span><b>drawing · BOM · subsystem</b></div></section>';
  }

  function sceneHTML(type, world) {
    if (!world) return '';
    return world.scene === 'quality' ? qualityScene(type) : engineeringScene(type);
  }

  function decorateMechanic(type, world) {
    const stage = main.querySelector('.game-stage');
    if (!stage) return;
    stage.dataset.productionScene = world.scene;
    stage.dataset.productionGame = type;

    const gauge = stage.querySelector('.quality-gauge');
    if (gauge) gauge.classList.add('gw30b-quality-gauge-enhanced');
    const spec = stage.querySelector('.spec-card');
    if (spec) spec.classList.add('gw30b-spec-enhanced');
    const bom = stage.querySelector('.bom-tree');
    if (bom) bom.classList.add('gw30b-bom-enhanced');
    const choices = stage.querySelector('.game-choice-grid');
    if (choices) choices.classList.add(world.scene === 'quality' ? 'gw30b-quality-decisions' : 'gw30b-engineering-decisions');
  }

  function cleanup() {
    if (pulseTimer) root.clearTimeout(pulseTimer);
    pulseTimer = null;
    main.classList.remove('gw30b-enabled','gw30b-engaged');
    main.removeAttribute('data-gw30b-scene');
    main.removeAttribute('data-gw30b-game');
    main.querySelectorAll('.gw30b-production-scene').forEach(function (node) { node.remove(); });
  }

  function decorate() {
    const type = activeType();
    const world = STAGE_B[type];
    const shell = main.querySelector('.game-session-shell,.game-lab-session');
    if (!world || !shell) {
      cleanup();
      return;
    }

    main.classList.add('gw30b-enabled');
    main.dataset.gw30bScene = world.scene;
    main.dataset.gw30bGame = type;

    if (!shell.querySelector('.gw30b-production-scene')) {
      const top = shell.querySelector('.game-session-top');
      if (top) top.insertAdjacentHTML('afterend', sceneHTML(type, world));
      else shell.insertAdjacentHTML('afterbegin', sceneHTML(type, world));
    }

    decorateMechanic(type, world);
    main.classList.remove('gw30b-engaged');
    if (pulseTimer) root.clearTimeout(pulseTimer);
    pulseTimer = root.setTimeout(function () { main.classList.add('gw30b-engaged'); }, 80);
  }

  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () {
      queued = false;
      decorate();
    });
  }

  new MutationObserver(schedule).observe(main, {childList:true, subtree:true});
  root.document.addEventListener('click', function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-v618-choice],[data-order-token],[data-order-done],[data-view="games"],[data-start-v618-game]')) {
      root.setTimeout(schedule, 0);
    }
  });
  root.addEventListener('popstate', schedule);
  schedule();
})(window);
