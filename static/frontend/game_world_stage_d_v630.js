/* v6.0.30 Stage D — process-specific automotive motion. Visual only: no scoring/API/XP behavior. */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const PROCESS_BY_GAME = Object.freeze({
    match:{family:'assembly',action:'line-call',tag:'LINE SIGNAL'},
    listening:{family:'assembly',action:'operator-call',tag:'OPERATOR CALL'},
    mistake:{family:'quality',action:'precision',tag:'PRECISION CHECK'},
    phrase:{family:'assembly',action:'work-instruction',tag:'WORK INSTRUCTION'},
    hotspot:{family:'assembly',action:'part-install',tag:'PART INSTALL'},
    assembly_order:{family:'assembly',action:'station-sequence',tag:'STATION SEQUENCE'},
    shop_route:{family:'logistics',action:'plant-route',tag:'PLANT ROUTE'},
    tool_select:{family:'assembly',action:'torque-verify',tag:'TORQUE VERIFY'},
    defect_detective:{family:'paint',action:'surface-scan',tag:'SURFACE SCAN'},
    safety_spot:{family:'welding',action:'safety-interlock',tag:'SAFETY INTERLOCK'},
    quality_gate:{family:'quality',action:'disposition',tag:'QUALITY DISPOSITION'},
    logistics_route:{family:'logistics',action:'agv-route',tag:'AGV ROUTE'},
    kanban:{family:'logistics',action:'replenishment',tag:'KANBAN REPLENISH'},
    bom_builder:{family:'engineering',action:'bom-thread',tag:'BOM DIGITAL THREAD'},
    spec_check:{family:'quality',action:'cmm-probe',tag:'CMM PROBE'},
    rapid_recall:{family:'factory',action:'takt-response',tag:'TAKT RESPONSE'},
    memory_pairs:{family:'assembly',action:'kitting',tag:'PART KITTING'},
    odd_one_out:{family:'engineering',action:'classification',tag:'SYSTEM CLASSIFICATION'},
    dialogue_choice:{family:'factory',action:'control-room',tag:'CONTROL ROOM'},
    shift_incident:{family:'welding',action:'containment',tag:'CONTAINMENT'}
  });

  let queued = false;
  let actionTimer = null;
  let lastSessionKey = '';
  let lastIndex = -1;

  function frontend() { return root.MGCFrontend || null; }
  function snapshot() {
    try {
      const f = frontend();
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }
  function sessionInfo() {
    const state = snapshot();
    const session = state.gameSessionV618 || state.gameSession || null;
    if (!session || !session.game_type) return null;
    return {
      type:String(session.game_type),
      index:Number(state.gameSessionV618 ? (state.gameIndexV618 || 0) : (state.gameIndex || 0)),
      total:Array.isArray(session.items) ? Math.min(5,session.items.length) : 5,
      key:String(session.session_id || session.id || session.game_type)
    };
  }
  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  function assemblyRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-assembly" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-assembly-cell"><div class="gw30d-car-shell"><i class="roof"></i><i class="body"></i><i class="wheel w1"></i><i class="wheel w2"></i></div>' +
      '<div class="gw30d-part"><i></i></div><div class="gw30d-driver"><i></i><b></b></div>' +
      '<div class="gw30d-torque-ring"><i></i><span>24 Nm</span></div><div class="gw30d-station-light"></div></div>' +
      '<div class="gw30d-process-track"><i></i><span>PART</span><span>FIT</span><span>VERIFY</span><span>RELEASE</span></div></div>';
  }

  function weldingRig(profile) {
    let points = '';
    for (let i=0;i<8;i+=1) points += '<i class="gw30d-weld-point p' + (i+1) + '"></i>';
    return '<div class="gw30d-rig gw30d-rig-welding" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-weld-process"><div class="gw30d-biw-shell">' + points + '</div><div class="gw30d-robot-motion"><i></i><b></b><em></em></div>' +
      '<div class="gw30d-weld-flash"></div><div class="gw30d-safety-beacon"><i></i></div></div>' +
      '<div class="gw30d-process-track"><i></i><span>CLAMP</span><span>WELD</span><span>CHECK</span><span>RELEASE</span></div></div>';
  }

  function paintRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-paint" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-paint-process"><div class="gw30d-painted-body"><i></i></div><div class="gw30d-spray-gun"><i></i><b></b></div>' +
      '<div class="gw30d-spray-cloud"></div><div class="gw30d-optical-bar"></div><span class="gw30d-film-readout">82 μm</span></div>' +
      '<div class="gw30d-process-track"><i></i><span>SPRAY</span><span>FLASH</span><span>SCAN</span><span>OK</span></div></div>';
  }

  function logisticsRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-logistics" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-logistics-process"><div class="gw30d-log-route"></div>' +
      '<span class="gw30d-log-node n1">DOCK</span><span class="gw30d-log-node n2">MARKET</span><span class="gw30d-log-node n3">LINE</span>' +
      '<div class="gw30d-agv"><i></i><b></b><em></em></div><div class="gw30d-container c1"></div><div class="gw30d-container c2"></div></div>' +
      '<div class="gw30d-process-track"><i></i><span>CALL</span><span>PICK</span><span>MOVE</span><span>DELIVER</span></div></div>';
  }

  function qualityRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-quality" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-quality-process"><div class="gw30d-measured-part"><i></i></div><div class="gw30d-cmm-gantry"><i></i><b></b><em></em></div>' +
      '<div class="gw30d-dimension"><small>ACTUAL</small><b>25.08</b><span>25.00 ± 0.20</span></div>' +
      '<div class="gw30d-tolerance-band"><i></i><b></b></div></div>' +
      '<div class="gw30d-process-track"><i></i><span>LOCATE</span><span>PROBE</span><span>COMPARE</span><span>STATUS</span></div></div>';
  }

  function engineeringRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-engineering" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-engineering-process"><div class="gw30d-blueprint"><i></i><i></i><b>REV C</b></div>' +
      '<div class="gw30d-data-link"><i></i><i></i><i></i></div><div class="gw30d-bom-stack"><span>VEHICLE</span><span>SYSTEM</span><span>MODULE</span><span>PART</span></div>' +
      '<div class="gw30d-release-chip">RELEASED</div></div>' +
      '<div class="gw30d-process-track"><i></i><span>DRAWING</span><span>LINK</span><span>BOM</span><span>RELEASE</span></div></div>';
  }

  function factoryRig(profile) {
    return '<div class="gw30d-rig gw30d-rig-factory" aria-hidden="true">' +
      '<div class="gw30d-rig-head"><small>PROCESS LIVE</small><b>' + esc(profile.tag) + '</b></div>' +
      '<div class="gw30d-factory-process"><div class="gw30d-andon"><span>LINE 01</span><b>58.4</b><small>TAKT s</small><i></i></div>' +
      '<div class="gw30d-comms"><i></i><i></i><i></i><b></b></div><div class="gw30d-response-pulse"></div></div>' +
      '<div class="gw30d-process-track"><i></i><span>NOTICE</span><span>DECIDE</span><span>CALL</span><span>CONFIRM</span></div></div>';
  }

  function rigHTML(profile) {
    if (profile.family === 'welding') return weldingRig(profile);
    if (profile.family === 'paint') return paintRig(profile);
    if (profile.family === 'logistics') return logisticsRig(profile);
    if (profile.family === 'quality') return qualityRig(profile);
    if (profile.family === 'engineering') return engineeringRig(profile);
    if (profile.family === 'factory') return factoryRig(profile);
    return assemblyRig(profile);
  }

  function processHost() {
    return main.querySelector('.gw30a-production-scene,.gw30b-production-scene,.game-session-shell,.game-lab-session,.quiz-stage');
  }

  function removeRig() {
    main.classList.remove('gw30d-enabled','gw30d-action');
    main.removeAttribute('data-gw30d-family');
    main.removeAttribute('data-gw30d-action');
    main.removeAttribute('data-gw30d-game');
    main.querySelectorAll('.gw30d-rig').forEach(function (node) { node.remove(); });
  }

  function progressRig(info) {
    const rig = main.querySelector('.gw30d-rig');
    if (!rig) return;
    const total = Math.max(1,Math.min(5,info.total || 5));
    const index = Math.max(0,Math.min(total-1,info.index || 0));
    rig.style.setProperty('--gw30d-progress', (((index + 1) / total) * 100).toFixed(0) + '%');
    rig.dataset.step = String(index + 1);
    const track = rig.querySelector('.gw30d-process-track');
    if (track) track.setAttribute('aria-label','Process step ' + (index + 1) + ' of ' + total);
  }

  function decorate() {
    const info = sessionInfo();
    if (!info || !PROCESS_BY_GAME[info.type]) {
      lastSessionKey = '';
      lastIndex = -1;
      removeRig();
      return;
    }
    const profile = PROCESS_BY_GAME[info.type];
    const host = processHost();
    if (!host) return;

    main.classList.add('gw30d-enabled');
    main.dataset.gw30dFamily = profile.family;
    main.dataset.gw30dAction = profile.action;
    main.dataset.gw30dGame = info.type;

    let rig = main.querySelector('.gw30d-rig');
    const sameRig = rig && rig.dataset.gameType === info.type;
    if (!sameRig) {
      if (rig) rig.remove();
      host.insertAdjacentHTML('beforeend',rigHTML(profile));
      rig = main.querySelector('.gw30d-rig');
      if (rig) {
        rig.dataset.gameType = info.type;
        rig.dataset.processAction = profile.action;
      }
    }
    progressRig(info);

    if (lastSessionKey === info.key && lastIndex >= 0 && info.index > lastIndex && rig) {
      rig.classList.remove('gw30d-step-advance');
      void rig.offsetWidth;
      rig.classList.add('gw30d-step-advance');
    }
    lastSessionKey = info.key;
    lastIndex = info.index;
  }

  function runAction(event) {
    if (!main.classList.contains('gw30d-enabled') || !event.target || !event.target.closest) return;
    const control = event.target.closest('[data-v618-choice],[data-hotspot-zone],[data-order-token],[data-order-done],[data-game-answer],#phraseDone,#playGameAudio,[data-play-v618-audio]');
    if (!control || control.disabled) return;
    const rig = main.querySelector('.gw30d-rig');
    if (!rig) return;

    main.classList.remove('gw30d-action');
    rig.classList.remove('gw30d-cycle');
    void rig.offsetWidth;
    main.classList.add('gw30d-action');
    rig.classList.add('gw30d-cycle');

    if (actionTimer) root.clearTimeout(actionTimer);
    actionTimer = root.setTimeout(function () {
      main.classList.remove('gw30d-action');
      if (rig) rig.classList.remove('gw30d-cycle');
    },980);
  }

  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () {
      queued = false;
      decorate();
    });
  }

  new MutationObserver(schedule).observe(main,{childList:true,subtree:true});
  root.document.addEventListener('click',runAction,true);
  root.document.addEventListener('click',function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-view="games"],[data-start-v618-game],[data-start-game],[data-replay-v618],[data-go-games-home],[data-go="games"]')) {
      root.setTimeout(schedule,0);
    }
  },true);
  root.addEventListener('popstate',schedule);
  schedule();
})(window);
