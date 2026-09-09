/* v6.0.30 — Animation & Interaction Stage.
 * Local presentation/learning enhancement for Assembly Builder and Powertrain Builder.
 * No API, XP or canonical scoring ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('animation-interaction-v630'))return;
  const q=(s,x)=>(x||root.document).querySelector(s);
  const qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reduced=()=>!!(root.matchMedia&&root.matchMedia('(prefers-reduced-motion: reduce)').matches);

  const TOOL_LIBRARY={
    torque:['Динамометрический гайковёрт','扭矩扳手','niǔjǔ bānshǒu','torque wrench'],
    manipulator:['Монтажный манипулятор','装配机械手','zhuāngpèi jīxièshǒu','assembly manipulator'],
    vacuum:['Вакуумный захват','真空吸盘','zhēnkōng xīpán','vacuum lifter'],
    scanner:['Оптический сканер','光学扫描仪','guāngxué sǎomiáoyí','optical scanner'],
    clip:['Клипсовый инструмент','卡扣工具','kǎkòu gōngjù','clip tool'],
    tester:['Диагностический тестер','诊断仪','zhěnduànyí','diagnostic tester'],
    stand:['Стенд сборки двигателя','发动机装配台','fādòngjī zhuāngpèi tái','engine assembly stand'],
    ring:['Оправка поршневых колец','活塞环压缩器','huósāihuán yāsuōqì','piston ring compressor'],
    injector:['Инструмент форсунки','喷油器工具','pēnyóuqì gōngjù','injector tool'],
    timing:['Фиксатор фаз ГРМ','正时定位工具','zhèngshí dìngwèi gōngjù','timing fixture'],
    pressure:['Тестер давления топлива','燃油压力测试仪','rányóu yālì cèshìyí','fuel pressure tester'],
    lock:['Фиксатор маховика','飞轮锁止工具','fēilún suǒzhǐ gōngjù','flywheel locking tool']
  };
  const ZONE_TOOL={
    wheel:'torque',drive_axle:'torque',front_door:'manipulator',rear_door:'manipulator',cab:'manipulator',cab_door:'manipulator',
    windshield:'vacuum',side_window:'vacuum',bumper:'clip',rear_bumper:'clip',grille:'clip',headlamp:'scanner',rear_lamp:'scanner',
    seat:'manipulator',driver_seat:'manipulator',passenger_seat:'manipulator',steering:'torque',seatbelt:'tester',cluster:'tester',display:'tester',nav:'tester',start:'tester',
    block:'stand',crank:'torque',piston:'ring',rod:'torque',head:'torque',cam:'timing',injector:'injector',intake:'manipulator',alternator:'torque',oil_filter:'torque',
    rail:'pressure',turbo:'torque',flywheel:'lock',hp_pump:'timing'
  };
  const TOOL_DISTRACTORS=['scanner','torque','manipulator','vacuum','tester','clip','stand','ring','pressure','timing'];

  const DEFECTS={
    car:{front_door:['Нарушен зазор двери','车门间隙异常','chēmén jiànxì yìcháng'],bumper:['Смещён передний бампер','前保险杠错位','qián bǎoxiǎnggàng cuòwèi'],wheel:['Момент затяжки вне допуска','车轮扭矩异常','chēlún niǔjǔ yìcháng'],headlamp:['Неверная посадка фары','前照灯安装异常','qiánzhàodēng ānzhuāng yìcháng'],windshield:['Нарушена герметизация стекла','挡风玻璃密封异常','dǎngfēng bōli mìfēng yìcháng']},
    truck:{cab_door:['Нарушен зазор двери кабины','驾驶室车门间隙异常','jiàshǐshì chēmén jiànxì yìcháng'],fuel_tank:['Ослаблено крепление бака','燃油箱固定异常','rányóuxiāng gùdìng yìcháng'],fifth_wheel:['Замок седла не подтверждён','鞍座锁止异常','ānzuò suǒzhǐ yìcháng'],wheel:['Момент колеса вне допуска','车轮扭矩异常','chēlún niǔjǔ yìcháng'],headlamp:['Неверное положение фары','前照灯位置异常','qiánzhàodēng wèizhì yìcháng']},
    carInterior:{seat:['Крепление сиденья не подтверждено','座椅固定异常','zuòyǐ gùdìng yìcháng'],seatbelt:['Маршрут ремня нарушен','安全带安装异常','ānquándài ānzhuāng yìcháng'],steering:['Рулевое колесо не отцентровано','方向盘位置异常','fāngxiàngpán wèizhì yìcháng'],cluster:['Разъём панели не подтверждён','仪表盘连接异常','yíbiǎopán liánjiē yìcháng'],start:['Кнопка запуска не отвечает','启动按钮功能异常','qǐdòng ànniǔ gōngnéng yìcháng']},
    truckInterior:{driver_seat:['Крепление сиденья водителя','驾驶员座椅固定异常','jiàshǐyuán zuòyǐ gùdìng yìcháng'],seatbelt:['Ремень безопасности установлен неверно','安全带安装异常','ānquándài ānzhuāng yìcháng'],steering:['Руль не отцентрирован','方向盘位置异常','fāngxiàngpán wèizhì yìcháng'],cluster:['Нет подтверждения приборной панели','仪表盘功能异常','yíbiǎopán gōngnéng yìcháng'],parking_brake:['Стояночный тормоз требует проверки','驻车制动异常','zhùchē zhìdòng yìcháng']},
    carEngine:{oil_filter:['След масла у фильтра','机油滤清器泄漏','jīyóu lǜqīngqì xièlòu'],injector:['Разъём форсунки не зафиксирован','喷油器连接异常','pēnyóuqì liánjiē yìcháng'],crank:['Осевой люфт коленвала вне допуска','曲轴间隙异常','qūzhóu jiànxì yìcháng'],head:['Затяжка ГБЦ требует проверки','气缸盖扭矩异常','qìgāng gài niǔjǔ yìcháng'],alternator:['Натяжение привода генератора','发电机传动异常','fādiànjī chuándòng yìcháng']},
    truckEngine:{hp_pump:['Фаза ТНВД требует проверки','高压油泵正时异常','gāoyā yóubèng zhèngshí yìcháng'],rail:['Давление Common Rail вне допуска','共轨压力异常','gòngguǐ yālì yìcháng'],injector:['Утечка в зоне форсунки','喷油器泄漏','pēnyóuqì xièlòu'],turbo:['Хомут турбокомпрессора не подтверждён','涡轮增压器连接异常','wōlún zēngyāqì liánjiē yìcháng'],flywheel:['Крепёж маховика требует контроля','飞轮紧固异常','fēilún jǐngù yìcháng']}
  };

  let toolMode=false, unlockedZone='', inspection=null, lastShell=null;
  function moduleApi(name){try{return frontend.get(name)}catch(_){return null}}
  function identify(shell){
    const title=(q('h1',shell)||{}).textContent||'';
    const assembly=moduleApi('assembly-builder-v630'),power=moduleApi('powertrain-builder-v630');
    const sources=[assembly&&assembly.modes,power&&power.modes].filter(Boolean);
    for(const modes of sources)for(const key of Object.keys(modes))if(title.trim()===modes[key].title)return {key,cfg:modes[key],power:!!(power&&modes===power.modes)};
    return null;
  }
  function language(shell){
    const active=q('[data-ab-lang].active,[data-pt-lang].active',shell);
    if(!active)return 'chinese';
    return active.dataset.abLang||active.dataset.ptLang||'chinese';
  }
  function currentZone(shell){const m=q('.ab3d-marker.current,.pt3d-marker.current',shell);return m&&m.dataset.zone||''}
  function toolName(id){return TOOL_LIBRARY[id]||TOOL_LIBRARY.tester}
  function toolLabel(id,lang){const t=toolName(id);return lang==='english'?t[3]:(t[1]+' · '+t[2])}

  function ensureToolbar(shell){
    if(q('.ai-toolbar',shell))return;
    const info=identify(shell);if(!info)return;
    const host=q('#ab3dHost,#pt3dHost',shell);if(!host)return;
    shell.dataset.aiMode=info.key;
    const toolbar=root.document.createElement('div');toolbar.className='ai-toolbar';
    toolbar.innerHTML='<button type="button" data-ai="tools">Инструменты: выкл</button><button type="button" data-ai="explode">Exploded View</button>'+
      (info.power?'<button type="button" data-ai="cutaway">Cutaway</button><button type="button" data-ai="flows">Потоки</button>':'')+
      '<button type="button" data-ai="camera">Камера</button>';
    const lang=q('.ab-language,.pt-language',shell);(lang&&lang.parentNode?lang.parentNode:shell).insertBefore(toolbar,lang?lang.nextSibling:shell.firstChild);
    toolbar.onclick=e=>{const b=e.target.closest('button[data-ai]');if(!b)return;const action=b.dataset.ai;
      if(action==='tools'){toolMode=!toolMode;b.classList.toggle('active',toolMode);b.textContent='Инструменты: '+(toolMode?'вкл':'выкл');unlockedZone='';ensureToolDock(shell)}
      if(action==='explode')toggleExploded(shell,b,info);
      if(action==='cutaway')toggleCutaway(shell,b,info);
      if(action==='flows'){host.classList.toggle('ai-flows');b.classList.toggle('active',host.classList.contains('ai-flows'));ensureCutawayLayer(shell,info)}
      if(action==='camera')runCamera(host,b);
    };
    ensureCutawayLayer(shell,info);ensureToolDock(shell);
  }

  function ensureToolDock(shell){
    let dock=q('.ai-tool-dock',shell);if(!dock){dock=root.document.createElement('div');dock.className='ai-tool-dock';const model=q('.ab-model,.pt-model',shell);if(model)model.appendChild(dock)}
    if(!dock)return;dock.classList.toggle('visible',toolMode);renderToolDock(shell);
  }
  function renderToolDock(shell){
    const dock=q('.ai-tool-dock',shell);if(!dock||!toolMode)return;const zone=currentZone(shell);if(!zone){dock.innerHTML='<span>ИНСТРУМЕНТ</span><b>Ожидание операции</b>';return}
    const correct=ZONE_TOOL[zone]||'tester',lang=language(shell),choices=[correct];for(const id of TOOL_DISTRACTORS){if(id!==correct&&!choices.includes(id))choices.push(id);if(choices.length===3)break}
    choices.sort((a,b)=>((zone.charCodeAt(0)+a.length)%3)-((zone.charCodeAt(0)+b.length)%3));
    dock.innerHTML='<span>ВЫБЕРИТЕ ИНСТРУМЕНТ</span><b>'+esc(zone.replaceAll('_',' '))+'</b><div>'+choices.map(id=>'<button type="button" data-ai-tool="'+id+'">'+esc(toolLabel(id,lang))+'</button>').join('')+'</div><small>Верный инструмент откроет установку узла.</small>';
    qa('[data-ai-tool]',dock).forEach(btn=>btn.onclick=()=>{if(btn.dataset.aiTool===correct){unlockedZone=zone;qa('[data-ai-tool]',dock).forEach(x=>x.classList.toggle('correct-tool',x===btn));dock.classList.add('tool-ready');const st=q('#abStatus,#ptStatus',shell);if(st)st.innerHTML='<b>Инструмент выбран.</b> Нажмите на подсвеченный узел для установки.'}else{btn.classList.add('wrong-tool');setTimeout(()=>btn.classList.remove('wrong-tool'),430)}});
  }

  function toggleExploded(shell,btn,info){
    const host=q('#ab3dHost,#pt3dHost',shell);if(!host)return;const on=!host.classList.contains('ai-exploded');host.classList.toggle('ai-exploded',on);btn.classList.toggle('active',on);btn.textContent=on?'Собрать вид':'Exploded View';
    let layer=q('.ai-exploded-layer',host);if(!layer){layer=root.document.createElement('div');layer.className='ai-exploded-layer';host.appendChild(layer)}
    if(!on){layer.innerHTML='';return}
    const entries=Object.entries(info.cfg.catalog).slice(0,12);layer.innerHTML='<div class="ai-exploded-core">EXPLODED<br><small>учебный разрез</small></div>'+entries.map(([id,z],i)=>{const a=(i/entries.length)*Math.PI*2,x=50+Math.cos(a)*40,y=50+Math.sin(a)*39;return '<button type="button" data-ai-part="'+id+'" style="left:'+x+'%;top:'+y+'%"><b>'+esc(z[1])+'</b><em>'+esc(z[2])+'</em><small>'+esc(z[0])+'</small></button>'}).join('');
    qa('[data-ai-part]',layer).forEach(part=>part.onclick=()=>showPartCard(shell,info,part.dataset.aiPart));
  }
  function showPartCard(shell,info,id){const z=info.cfg.catalog[id];if(!z)return;let card=q('.ai-part-card',shell);if(!card){card=root.document.createElement('div');card.className='ai-part-card';const host=q('#ab3dHost,#pt3dHost',shell);host&&host.appendChild(card)}if(card)card.innerHTML='<button type="button" aria-label="Закрыть">×</button><span>УЗЕЛ 3D-МОДЕЛИ</span><h3>'+esc(z[1])+'</h3><em>'+esc(z[2])+'</em><b>'+esc(z[0])+'</b><small>'+esc(z[3])+'</small>';const close=q('button',card);if(close)close.onclick=()=>card.remove()}

  function ensureCutawayLayer(shell,info){if(!info.power)return;const host=q('#pt3dHost',shell);if(!host||q('.ai-cutaway-layer',host))return;const truck=info.key==='truckEngine',count=truck?6:4;const layer=root.document.createElement('div');layer.className='ai-cutaway-layer';layer.innerHTML='<div class="ai-xray-block"><div class="ai-valves">'+Array.from({length:count},(_,i)=>'<i style="--n:'+i+'"></i>').join('')+'</div><div class="ai-cylinders">'+Array.from({length:count},(_,i)=>'<span style="--n:'+i+'"><b></b><em></em></span>').join('')+'</div><div class="ai-crank"><i></i></div></div><div class="ai-flow air"><b>空气 · kōngqì</b></div><div class="ai-flow fuel"><b>'+(truck?'高压燃油 · gāoyā rányóu':'燃油 · rányóu')+'</b></div><div class="ai-flow exhaust"><b>排气 · páiqì</b></div><div class="ai-xray-legend"><span>Поршни</span><span>Коленвал</span><span>'+(truck?'Common Rail':'Зажигание')+'</span></div>';host.appendChild(layer)}
  function toggleCutaway(shell,btn,info){const host=q('#pt3dHost',shell);if(!host)return;ensureCutawayLayer(shell,info);const on=!host.classList.contains('ai-cutaway');host.classList.toggle('ai-cutaway',on);btn.classList.toggle('active',on);btn.textContent=on?'Обычный вид':'Cutaway'}

  function runCamera(host,btn){if(!host)return;host.classList.remove('ai-camera-run');void host.offsetWidth;host.classList.add('ai-camera-run');btn&&btn.classList.add('active');setTimeout(()=>{host.classList.remove('ai-camera-run');btn&&btn.classList.remove('active')},reduced()?50:3600)}
  function installationFx(shell,marker){
    const host=q('#ab3dHost,#pt3dHost',shell);if(!host||marker.dataset.aiFxDone)return;marker.dataset.aiFxDone='1';const r=host.getBoundingClientRect(),m=marker.getBoundingClientRect(),x=(m.left+m.width/2-r.left)/Math.max(r.width,1)*100,y=(m.top+m.height/2-r.top)/Math.max(r.height,1)*100,zone=marker.dataset.zone||'',tool=toolName(ZONE_TOOL[zone]||'tester');
    const rig=root.document.createElement('div');rig.className='ai-install-rig';rig.style.setProperty('--tx',x+'%');rig.style.setProperty('--ty',y+'%');rig.innerHTML='<div class="ai-flying-part"><span>POSITION</span><b>'+esc(zone.replaceAll('_',' '))+'</b></div><div class="ai-live-tool"><span>TOOL</span><b>'+esc(tool[0])+'</b><small>'+esc(tool[1])+' · '+esc(tool[2])+'</small></div><div class="ai-torque-ring"><i></i><b>LOCK</b></div>';host.appendChild(rig);host.classList.add('ai-focus-install');host.style.setProperty('--focus-x',(50-x)*.05+'%');host.style.setProperty('--focus-y',(50-y)*.05+'%');setTimeout(()=>rig.classList.add('positioned'),reduced()?0:120);setTimeout(()=>rig.classList.add('tooling'),reduced()?0:520);setTimeout(()=>rig.classList.add('locked'),reduced()?0:980);setTimeout(()=>{host.classList.remove('ai-focus-install');rig.remove();unlockedZone='';renderToolDock(shell)},reduced()?80:1650)
  }

  function ensureCompletionUpgrade(shell){
    const complete=q('.ab-complete-card,.pt-complete-card',shell);if(!complete||complete.dataset.aiUpgraded)return;complete.dataset.aiUpgraded='1';const info=identify(shell);if(!info)return;const host=q('#ab3dHost,#pt3dHost',shell);if(host)runCompletionSequence(host,info);
    const actions=q('.ab-complete-actions,.pt-complete-actions',complete);if(actions){const b=root.document.createElement('button');b.type='button';b.className='ghost ai-inspector-button';b.textContent=info.power?'Диагностика 3D':'3D Quality Inspector';b.onclick=()=>startInspection(shell,info);actions.insertBefore(b,actions.firstChild)}
  }
  function runCompletionSequence(host,info){let seq=q('.ai-completion-sequence',host);if(seq)seq.remove();seq=root.document.createElement('div');seq.className='ai-completion-sequence';const truck=info.key==='truck'||info.key==='truckEngine'||info.key==='truckInterior';const interior=info.key==='carInterior'||info.key==='truckInterior';const stages=info.power?(truck?['OIL PRESSURE','RAIL PRESSURE','COMBUSTION','ENGINE READY']:['OIL PRESSURE','IGNITION','COMBUSTION','ENGINE READY']):(interior?['POWER ON','CLUSTER CHECK','SAFETY SYSTEM','READY']:['SYSTEM CHECK','LIGHTS ON','ENGINE START','READY']);seq.innerHTML='<span>MGC · START-UP SEQUENCE</span><b>'+stages[0]+'</b><div>'+stages.map((s,i)=>'<i data-stage="'+i+'"></i>').join('')+'</div>';host.appendChild(seq);let i=0;const step=()=>{const label=q('b',seq);if(label)label.textContent=stages[i];qa('i',seq).forEach((dot,n)=>dot.classList.toggle('done',n<=i));host.dataset.aiStage=String(i);if(++i<stages.length)setTimeout(step,reduced()?20:650);else setTimeout(()=>seq.classList.add('finished'),reduced()?30:850)};step()}

  function startInspection(shell,info){
    const host=q('#ab3dHost,#pt3dHost',shell);if(!host)return;const defects=DEFECTS[info.key]||{};let ids=Object.keys(defects).filter(id=>q('[data-zone="'+id+'"]',host));if(ids.length<3)return;ids=ids.sort(()=>Math.random()-.5).slice(0,3);inspection={shell,info,ids,found:new Set()};host.classList.add('ai-inspection');qa('.ab3d-marker,.pt3d-marker',host).forEach(m=>{m.classList.remove('ai-defect-found','ai-inspected-ok');m.dataset.aiInspect='1'});let panel=q('.ai-inspection-panel',shell);if(panel)panel.remove();panel=root.document.createElement('div');panel.className='ai-inspection-panel';panel.innerHTML='<span>MGC · '+(info.power?'POWERTRAIN INSPECTION':'QUALITY INSPECTOR')+'</span><h3>Найдите 3 отклонения</h3><p>Поворачивайте модель и проверяйте узлы. Неисправности не подсвечиваются заранее.</p><div class="ai-inspection-progress"><b>0 / 3</b><i><em></em></i></div><div class="ai-inspection-result">Начните осмотр модели.</div><button type="button" class="ghost">Завершить осмотр</button>';const model=q('.ab-model,.pt-model',shell);model&&model.appendChild(panel);q('button',panel).onclick=()=>stopInspection(shell);runCamera(host,null)
  }
  function inspectMarker(marker){if(!inspection||!inspection.shell.contains(marker))return false;const id=marker.dataset.zone,def=DEFECTS[inspection.info.key]&&DEFECTS[inspection.info.key][id],panel=q('.ai-inspection-panel',inspection.shell);if(!panel)return true;const result=q('.ai-inspection-result',panel),lang=language(inspection.shell);if(inspection.ids.includes(id)){inspection.found.add(id);marker.classList.add('ai-defect-found');result.innerHTML='<b>ДЕФЕКТ НАЙДЕН</b><strong>'+esc(def[0])+'</strong>'+(lang==='english'?'':'<em>'+esc(def[1])+' · '+esc(def[2])+'</em>')}else{marker.classList.add('ai-inspected-ok');result.innerHTML='<b class="ok">OK</b><strong>Узел соответствует визуальному контролю.</strong>'}const n=inspection.found.size,qb=q('.ai-inspection-progress b',panel),bar=q('.ai-inspection-progress em',panel);if(qb)qb.textContent=n+' / 3';if(bar)bar.style.width=(n/3*100)+'%';if(n===3){panel.classList.add('passed');result.innerHTML='<b class="ok">QUALITY · PASS</b><strong>Все три отклонения обнаружены.</strong><em>Контроль завершён.</em>';setTimeout(()=>stopInspection(inspection&&inspection.shell,true),reduced()?30:1300)}return true}
  function stopInspection(shell,passed){if(!shell)return;const host=q('#ab3dHost,#pt3dHost',shell);host&&host.classList.remove('ai-inspection');qa('[data-ai-inspect]',shell).forEach(m=>delete m.dataset.aiInspect);const panel=q('.ai-inspection-panel',shell);if(panel&&passed)panel.classList.add('passed-final');if(panel&&!passed)panel.remove();inspection=null}

  function installCapture(){root.document.addEventListener('click',e=>{const marker=e.target.closest&&e.target.closest('.ab3d-marker,.pt3d-marker');if(!marker)return;const shell=marker.closest('.ab-shell,.pt-shell');if(!shell)return;if(inspection&&inspection.shell===shell){e.preventDefault();e.stopImmediatePropagation();inspectMarker(marker);return}if(!toolMode||!marker.classList.contains('current'))return;const zone=marker.dataset.zone;if(unlockedZone!==zone){e.preventDefault();e.stopImmediatePropagation();const dock=q('.ai-tool-dock',shell);dock&&dock.classList.add('attention');setTimeout(()=>dock&&dock.classList.remove('attention'),450)}},true)}

  function scan(){const shell=q('.ab-shell,.pt-shell');if(!shell)return;if(shell!==lastShell){lastShell=shell;unlockedZone='';inspection=null}ensureToolbar(shell);ensureToolDock(shell);ensureCompletionUpgrade(shell);const current=q('.ab3d-marker.current,.pt3d-marker.current',shell);if(current&&current.dataset.aiCurrent!=='1'){qa('[data-ai-current]',shell).forEach(x=>delete x.dataset.aiCurrent);current.dataset.aiCurrent='1';renderToolDock(shell)}qa('.ab3d-marker.correct,.pt3d-marker.correct',shell).forEach(m=>installationFx(shell,m))}
  let scheduled=false;function schedule(){if(scheduled)return;scheduled=true;root.requestAnimationFrame(()=>{scheduled=false;scan()})}
  function install(){installCapture();scan();new MutationObserver(schedule).observe(root.document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class']})}
  frontend.register('animation-interaction-v630',{install,scan,defects:DEFECTS,tools:TOOL_LIBRARY});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
