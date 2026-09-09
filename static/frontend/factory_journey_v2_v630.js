/* v6.0.30 Stage E — Factory Journey 2.0. Orchestration/presentation only: canonical Game Lab owns answers, scoring, XP and API. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) return;
  if (frontend.has && frontend.has('factory-journey-v2-v630')) return;

  const STAGES = Object.freeze([
    {
      id:'supplier', zone:'Supplier', topic:'Поставщики и закупки', game:'dialogue_choice', index:'01',
      labelRu:'Поставщик', labelEn:'Supplier', labelZh:'供应商', pinyin:'gōngyìngshāng',
      incidentRu:'Поставщик спрашивает, утверждена ли актуальная ревизия чертежа перед отгрузкой.',
      incidentEn:'The supplier asks whether the latest drawing revision is approved before shipment.',
      incidentZh:'供应商询问最新图纸版本是否已批准后再发货。',
      incidentPy:'gōngyìngshāng xúnwèn zuìxīn túzhǐ bǎnběn shìfǒu yǐ pīzhǔn hòu zài fāhuò',
      calloutEn:'Confirm drawing revision', calloutZh:'确认图纸版本', calloutPy:'quèrèn túzhǐ bǎnběn'
    },
    {
      id:'logistics', zone:'Logistics', topic:'Логистика JIT/JIS', game:'logistics_route', index:'02',
      labelRu:'Логистика', labelEn:'Logistics', labelZh:'物流', pinyin:'wùliú',
      incidentRu:'На станции 24 заканчивается материал. Нужно подтвердить маршрут пополнения до остановки линии.',
      incidentEn:'Station 24 is running short of material. Confirm the replenishment route before the line stops.',
      incidentZh:'24号工位即将缺料，请在线停之前确认补料路线。',
      incidentPy:'èrshísì hào gōngwèi jíjiāng quēliào, qǐng zài xiàn tíng zhīqián quèrèn bǔliào lùxiàn',
      calloutEn:'Confirm replenishment route', calloutZh:'确认补料路线', calloutPy:'quèrèn bǔliào lùxiàn'
    },
    {
      id:'welding', zone:'Welding', topic:'Сварка', game:'shift_incident', index:'03',
      labelRu:'Сварка', labelEn:'Welding', labelZh:'焊装', pinyin:'hànzhuāng',
      incidentRu:'Сварочный робот остановился. Перед перезапуском нужно корректно обсудить interlock и containment.',
      incidentEn:'The welding robot has stopped. Confirm the safety interlock and containment before restart.',
      incidentZh:'焊接机器人已停止，重启前请确认安全联锁和遏制措施。',
      incidentPy:'hànjiē jīqìrén yǐ tíngzhǐ, chóngqǐ qián qǐng quèrèn ānquán liánsuǒ hé èzhì cuòshī',
      calloutEn:'Safety interlock check', calloutZh:'安全联锁检查', calloutPy:'ānquán liánsuǒ jiǎnchá'
    },
    {
      id:'paint', zone:'Paint', topic:'Окраска', game:'defect_detective', index:'04',
      labelRu:'Окраска', labelEn:'Paint', labelZh:'涂装', pinyin:'túzhuāng',
      incidentRu:'На окрашенной панели обнаружено отклонение. Нужно определить дефект и правильно сообщить о нём.',
      incidentEn:'A painted panel is out of standard. Identify the surface defect and report it correctly.',
      incidentZh:'涂装面板出现异常，请识别表面缺陷并正确报告。',
      incidentPy:'túzhuāng miànbǎn chūxiàn yìcháng, qǐng shíbié biǎomiàn quēxiàn bìng zhèngquè bàogào',
      calloutEn:'Inspect painted surface', calloutZh:'检查涂装表面', calloutPy:'jiǎnchá túzhuāng biǎomiàn'
    },
    {
      id:'assembly', zone:'Assembly', topic:'Сборка автомобиля', game:'tool_select', index:'05',
      labelRu:'Сборка', labelEn:'Assembly', labelZh:'总装', pinyin:'zǒngzhuāng',
      incidentRu:'На переднем бампере требуется контроль крепежа. Выберите правильный инструмент и рабочую команду.',
      incidentEn:'The front bumper fastening needs verification. Select the correct tool and work instruction.',
      incidentZh:'前保险杠紧固需要确认，请选择正确工具和作业指令。',
      incidentPy:'qián bǎoxiǎnggàng jǐngù xūyào quèrèn, qǐng xuǎnzé zhèngquè gōngjù hé zuòyè zhǐlìng',
      calloutEn:'Verify fastening operation', calloutZh:'确认紧固操作', calloutPy:'quèrèn jǐngù cāozuò'
    },
    {
      id:'quality', zone:'Quality', topic:'Качество в автопроме', game:'spec_check', index:'06',
      labelRu:'Качество', labelEn:'Quality', labelZh:'质量', pinyin:'zhìliàng',
      incidentRu:'Измерение зазора требует решения по допуску. Проверьте спецификацию до disposition.',
      incidentEn:'A gap measurement requires a tolerance decision. Check the specification before disposition.',
      incidentZh:'间隙测量需要公差判定，请在处置前确认规格。',
      incidentPy:'jiànxì cèliáng xūyào gōngchā pàndìng, qǐng zài chǔzhì qián quèrèn guīgé',
      calloutEn:'Check tolerance and status', calloutZh:'确认公差和状态', calloutPy:'quèrèn gōngchā hé zhuàngtài'
    },
    {
      id:'engineering', zone:'Engineering', topic:'Инженерная документация', game:'bom_builder', index:'07',
      labelRu:'Инженерия', labelEn:'Engineering', labelZh:'工程', pinyin:'gōngchéng',
      incidentRu:'На линии обнаружено несоответствие между чертежом и BOM. Нужно проверить структуру и ревизию.',
      incidentEn:'The line found a mismatch between the drawing and BOM. Verify the structure and current revision.',
      incidentZh:'生产线发现图纸与BOM不一致，请确认结构和当前版本。',
      incidentPy:'shēngchǎnxiàn fāxiàn túzhǐ yǔ BOM bù yízhì, qǐng quèrèn jiégòu hé dāngqián bǎnběn',
      calloutEn:'Verify drawing → BOM', calloutZh:'确认图纸 → BOM', calloutPy:'quèrèn túzhǐ dào BOM'
    }
  ]);

  let observer = null;
  let queued = false;
  let installed = false;

  function stateApi() { try { return frontend.get('app-state'); } catch (_) { return null; } }
  function gameLab() { try { return frontend.get('game-lab-v618'); } catch (_) { return null; } }
  function engagement() { try { return frontend.get('game-engagement-v618'); } catch (_) { return null; } }
  function snapshot() {
    try {
      const api = stateApi();
      return api && api.current ? api.current() : {};
    } catch (_) { return {}; }
  }
  function progress() {
    try {
      const api = engagement();
      const value = api && api.progress ? api.progress() : null;
      return value && typeof value === 'object' ? value : {completed:{},best:{},tried:{}};
    } catch (_) { return {completed:{},best:{},tried:{}}; }
  }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g,function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }
  function isChinese() { return snapshot().language === 'chinese'; }
  function done(stage,data) { return Number((data.completed || {})[stage.game] || 0) > 0; }
  function best(stage,data) { return Math.max(0,Math.min(5,Number((data.best || {})[stage.game] || 0))); }
  function unlocked(index,data) {
    if (index === 0) return true;
    for (let i=0;i<index;i+=1) if (!done(STAGES[i],data)) return false;
    return true;
  }
  function summary(data) {
    const completed = STAGES.filter(function (stage) { return done(stage,data); }).length;
    const perfect = STAGES.filter(function (stage) { return best(stage,data) >= 5; }).length;
    return {completed:completed,perfect:perfect,pct:Math.round((completed / STAGES.length) * 100)};
  }
  function activeIndex(data) {
    for (let i=0;i<STAGES.length;i+=1) if (unlocked(i,data) && !done(STAGES[i],data)) return i;
    return STAGES.length - 1;
  }
  function stageState(stage,index,data,current) {
    if (done(stage,data)) return 'trained';
    if (index === current && unlocked(index,data)) return 'active';
    return unlocked(index,data) ? 'ready' : 'pending';
  }
  function languageIncident(stage) {
    if (isChinese()) {
      return '<p class="fj2-incident-main zh">' + esc(stage.incidentZh) + '</p>' +
        '<p class="fj2-pinyin">' + esc(stage.incidentPy) + '</p>' +
        '<p class="fj2-incident-helper">' + esc(stage.incidentRu) + '</p>';
    }
    return '<p class="fj2-incident-main">' + esc(stage.incidentEn) + '</p>' +
      '<p class="fj2-incident-helper">' + esc(stage.incidentRu) + '</p>';
  }
  function languageCallout(stage) {
    if (isChinese()) return '<b>' + esc(stage.calloutZh) + '</b><small>' + esc(stage.calloutPy) + '</small>';
    return '<b>' + esc(stage.calloutEn) + '</b><small>' + esc(stage.labelRu) + '</small>';
  }
  function stageLabel(stage) {
    if (isChinese()) return '<b>' + esc(stage.labelZh) + '</b><small>' + esc(stage.pinyin) + '</small>';
    return '<b>' + esc(stage.labelEn) + '</b><small>' + esc(stage.labelRu) + '</small>';
  }
  function stateLabel(state,score) {
    if (isChinese()) {
      if (state === 'trained') return '已训练 · ' + score + '/5';
      if (state === 'active') return '当前任务';
      if (state === 'ready') return '可开始';
      return '待解锁';
    }
    if (state === 'trained') return 'TRAINED · ' + score + '/5';
    if (state === 'active') return 'ACTIVE INCIDENT';
    if (state === 'ready') return 'READY';
    return 'PENDING';
  }
  function lineState(stage) {
    if (isChinese()) {
      const map = {supplier:'版本确认',logistics:'缺料预警',welding:'设备暂停',paint:'表面检查',assembly:'扭矩确认',quality:'公差判定',engineering:'版本核对'};
      return map[stage.id] || '生产运行';
    }
    const map = {supplier:'REVISION CHECK',logistics:'MATERIAL CALL',welding:'ROBOT HOLD',paint:'SURFACE CHECK',assembly:'TORQUE CHECK',quality:'TOLERANCE CHECK',engineering:'REVISION SYNC'};
    return map[stage.id] || 'LINE RUNNING';
  }
  function vehiclePhase(completed) {
    if (completed >= 7) return isChinese() ? '工程放行' : 'ENGINEERING RELEASED';
    if (completed >= 6) return isChinese() ? '质量确认' : 'QUALITY VERIFIED';
    if (completed >= 5) return isChinese() ? '总装完成' : 'FINAL ASSEMBLY';
    if (completed >= 4) return isChinese() ? '涂装车身' : 'PAINTED BODY';
    if (completed >= 3) return isChinese() ? '白车身' : 'BODY-IN-WHITE';
    return isChinese() ? '物料准备' : 'MATERIAL PREP';
  }
  function routeHTML(data,current) {
    return STAGES.map(function (stage,index) {
      const state = stageState(stage,index,data,current);
      const disabled = state === 'pending';
      return '<button type="button" class="fj2-route-node ' + state + '" data-fj2-stage="' + esc(stage.id) + '"' + (disabled ? ' disabled' : '') + '>' +
        '<span class="fj2-route-index">' + esc(stage.index) + '</span><span class="fj2-route-label">' + stageLabel(stage) + '</span>' +
        '<em>' + esc(stateLabel(state,best(stage,data))) + '</em></button>';
    }).join('');
  }
  function twinRows(data,current) {
    return STAGES.map(function (stage,index) {
      const state = stageState(stage,index,data,current);
      const status = state === 'trained' ? (isChinese() ? '已完成' : 'TRAINED') : state === 'active' ? (isChinese() ? '处理中' : 'ACTION') : state === 'ready' ? (isChinese() ? '待命' : 'READY') : (isChinese() ? '等待' : 'WAIT');
      return '<div class="fj2-twin-row ' + state + '"><span>' + esc(stage.labelRu) + '</span><i></i><b>' + esc(status) + '</b></div>';
    }).join('');
  }
  function carHTML(completed) {
    return '<div class="fj2-car" data-build-step="' + completed + '" aria-hidden="true">' +
      '<div class="fj2-car-shadow"></div><div class="fj2-car-biw"><i class="roof"></i><i class="body"></i><i class="wheel w1"></i><i class="wheel w2"></i></div>' +
      '<div class="fj2-car-paint"></div><div class="fj2-car-trim"><i></i><b></b></div><div class="fj2-car-quality"></div><div class="fj2-car-data"><i></i><i></i><i></i></div>' +
      '</div>';
  }
  function launch(stage) {
    const api = stateApi();
    const lab = gameLab();
    if (!lab || !lab.startGame) return;
    if (api && api.set) api.set('topic',String(stage.topic || ''));
    Promise.resolve(lab.startGame(stage.game)).catch(function () { /* canonical Game Lab owns error UI */ });
  }
  function signature(data) {
    return (isChinese() ? 'zh' : 'en') + '|' + STAGES.map(function (stage,index) {
      return stage.id + ':' + (done(stage,data) ? 1 : 0) + ':' + best(stage,data) + ':' + (unlocked(index,data) ? 1 : 0);
    }).join('|');
  }
  function render() {
    const main = root.document.getElementById('main');
    if (!main) return;
    const catalog = main.querySelector('.game-lab-grid');
    const legacy = main.querySelector('.factory-journey-v619');
    const session = main.querySelector('.game-session-shell,.game-lab-session,.quiz-stage');
    if (!catalog || session) {
      const existing = main.querySelector('.factory-journey-v2-v630');
      if (existing) existing.remove();
      if (legacy) legacy.classList.remove('fj2-superseded');
      return;
    }

    const data = progress();
    const sum = summary(data);
    const current = activeIndex(data);
    const stage = STAGES[current];
    const sig = signature(data);
    const existing = main.querySelector('.factory-journey-v2-v630');
    if (existing && existing.dataset.signature === sig) {
      if (legacy) legacy.classList.add('fj2-superseded');
      return;
    }
    if (existing) existing.remove();
    if (legacy) legacy.classList.add('fj2-superseded');

    const section = root.document.createElement('section');
    section.className = 'factory-journey-v2-v630';
    section.dataset.signature = sig;
    section.dataset.currentStage = stage.id;
    section.innerHTML =
      '<div class="fj2-shiftbar"><div><span>07:45</span><b>' + (isChinese() ? '班次模拟' : 'SHIFT SIMULATION') + '</b><small>' + (isChinese() ? '汽车工厂沟通路线' : 'Automotive communication route') + '</small></div>' +
      '<div class="fj2-shift-status"><i></i><span>' + (isChinese() ? '当前状态' : 'LINE STATUS') + '</span><b>' + esc(lineState(stage)) + '</b></div></div>' +
      '<div class="fj2-head"><div><span class="kicker">FACTORY JOURNEY 2.0 · v6.0.30</span><h2>' + (isChinese() ? '完成一整班的汽车工厂任务' : 'Пройдите рабочую смену автомобильного завода') + '</h2>' +
      '<p>' + (isChinese() ? '从供应商到工程部门，处理七个真实生产情境。每个任务使用现有的正式游戏机制和服务器评分。' : 'Семь связанных рабочих ситуаций: от поставщика и материального потока до сварки, окраски, сборки, качества и инженерной документации. Каждая миссия запускает существующую игровую механику.') + '</p></div>' +
      '<div class="fj2-progress-card"><span>' + (isChinese() ? '班次进度' : 'SHIFT PROGRESS') + '</span><b>' + sum.completed + '/7</b><small>' + esc(vehiclePhase(sum.completed)) + '</small><div><i style="width:' + sum.pct + '%"></i></div></div></div>' +
      '<div class="fj2-route" aria-label="Factory Journey 2.0">' + routeHTML(data,current) + '<div class="fj2-route-line"><i style="width:' + sum.pct + '%"></i></div></div>' +
      '<div class="fj2-workspace"><article class="fj2-incident"><div class="fj2-incident-top"><span>' + (isChinese() ? '当前事件' : 'CURRENT INCIDENT') + '</span><b>' + esc(stage.index) + ' · ' + esc(isChinese() ? stage.labelZh : stage.labelEn) + '</b></div>' +
      languageIncident(stage) + '<div class="fj2-action-callout">' + languageCallout(stage) + '</div>' +
      '<button type="button" class="primary fj2-launch" data-fj2-launch="' + esc(stage.id) + '">' + (isChinese() ? '开始任务 →' : 'Начать миссию →') + '</button></article>' +
      '<article class="fj2-vehicle-panel"><div class="fj2-panel-title"><span>DIGITAL VEHICLE</span><b>' + esc(vehiclePhase(sum.completed)) + '</b></div>' + carHTML(sum.completed) +
      '<div class="fj2-build-track"><span class="' + (sum.completed>=3?'on':'') + '">BIW</span><span class="' + (sum.completed>=4?'on':'') + '">PAINT</span><span class="' + (sum.completed>=5?'on':'') + '">ASSEMBLY</span><span class="' + (sum.completed>=6?'on':'') + '">QUALITY</span><span class="' + (sum.completed>=7?'on':'') + '">RELEASE</span></div></article>' +
      '<aside class="fj2-twin"><div class="fj2-panel-title"><span>FACTORY TWIN</span><b>' + (isChinese() ? '工位状态' : 'STATION STATUS') + '</b></div>' + twinRows(data,current) +
      '<div class="fj2-twin-footer"><b>' + sum.perfect + '</b><span>' + (isChinese() ? '个 5/5 任务' : 'миссий 5/5') + '</span></div></aside></div>';

    const anchor = legacy || catalog;
    anchor.parentNode.insertBefore(section,anchor);

    section.querySelectorAll('[data-fj2-stage]:not(:disabled)').forEach(function (button) {
      button.addEventListener('click',function () {
        const selected = STAGES.find(function (item) { return item.id === button.dataset.fj2Stage; });
        if (!selected) return;
        const selectedIndex = STAGES.indexOf(selected);
        if (!unlocked(selectedIndex,data)) return;
        launch(selected);
      });
    });
    const launchButton = section.querySelector('[data-fj2-launch]');
    if (launchButton) launchButton.addEventListener('click',function () { launch(stage); });
  }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; render(); });
  }
  function install() {
    if (installed) return;
    installed = true;
    const main = root.document.getElementById('main');
    if (main) {
      observer = new MutationObserver(schedule);
      observer.observe(main,{childList:true,subtree:true});
    }
    root.document.addEventListener('mgc:state-change',schedule);
    root.document.addEventListener('click',function (event) {
      if (event.target && event.target.closest && event.target.closest('[data-view="games"],[data-go-games-home],[data-go="games"],[data-replay-v618]')) root.setTimeout(schedule,0);
    },true);
    schedule();
  }

  frontend.register('factory-journey-v2-v630',{
    install:install,
    reconcile:schedule,
    stages:STAGES,
    summary:function () { return summary(progress()); }
  });

  if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded',install,{once:true});
  else install();
})(window);
