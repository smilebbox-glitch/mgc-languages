/* v6.0.30 — Factory Process Simulator.
 * Separate special training simulator: stamping -> welding -> paint -> assembly -> quality -> dealer.
 * Russian product chrome, Chinese/Pinyin or English learning content. No XP/API/canonical scoring ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('factory-process-simulator-v630'))return;
  const q=(s,x)=>(x||root.document).querySelector(s),qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const app=()=>{try{return frontend.get('app-state').current()}catch(_){return{language:'chinese',view:'games'}}};
  const CH=(id,ru,zh,py,en,correct,choices,visual)=>({id,ru,zh,py,en,correct,choices,visual});
  const C=(id,ru,zh,py,en)=>({id,ru,zh,py,en});

  const STAGES=Object.freeze([
    {id:'stamping',n:1,title:'Штамповка',zh:'冲压',py:'chōngyā',en:'Stamping',copy:'Из листовой стали получаем кузовные панели и проверяем геометрию после пресса.',operations:[
      CH('blank','Подайте листовую заготовку в пресс','板料上料','bǎnliào shàngliào','Load the sheet-metal blank','feeder',[C('feeder','Роликовая подача','送料机','sòngliào jī','Blank feeder'),C('weldgun','Сварочные клещи','焊钳','hànqián','Welding gun'),C('spray','Краскопульт','喷枪','pēnqiāng','Spray gun')],'blank-feed'),
      CH('die','Проверьте штамп перед рабочим циклом','模具检查','mújù jiǎnchá','Inspect the die before the cycle','diecheck',[C('diecheck','Контроль штампа','模具检查','mújù jiǎnchá','Die inspection'),C('torque','Затяжка колеса','车轮拧紧','chēlún nǐngjǐn','Wheel torque'),C('pdi','Предпродажная проверка','交付前检查','jiāofù qián jiǎnchá','PDI')],'die-check'),
      CH('press','Запустите формование панели','冲压成形','chōngyā chéngxíng','Stamp and form the panel','press',[C('press','Рабочий цикл пресса','压力机循环','yālìjī xúnhuán','Press cycle'),C('scan','Сканирование кузова','车身扫描','chēshēn sǎomiáo','Body scan'),C('engine','Запуск двигателя','发动机启动','fādòngjī qǐdòng','Engine start')],'press-cycle')
    ]},
    {id:'welding',n:2,title:'Сварка кузова',zh:'焊装',py:'hànzhuāng',en:'Body Welding',copy:'Панели фиксируются в оснастке, роботы и сварочные клещи формируют BIW — кузов в белом.',operations:[
      CH('fixture','Зафиксируйте боковину в сварочной оснастке','夹具定位','jiājù dìngwèi','Locate the side panel in the fixture','fixture',[C('fixture','Сварочная оснастка','焊装夹具','hànzhuāng jiājù','Welding fixture'),C('paintbooth','Окрасочная камера','喷漆室','pēnqī shì','Paint booth'),C('roller','Испытательный стенд','试验台','shìyàntái','Test bench')],'fixture-lock'),
      CH('spot','Выполните роботизированную точечную сварку','点焊','diǎnhàn','Perform robotic spot welding','weldgun',[C('weldgun','Сварочные клещи','焊钳','hànqián','Welding gun'),C('vacuum','Вакуумный захват','真空吸盘','zhēnkōng xīpán','Vacuum gripper'),C('scanner','Диагностический сканер','诊断仪','zhěnduànyí','Diagnostic scanner')],'spot-weld'),
      CH('weldcheck','Проверьте сварочные точки кузова','焊点检查','hàndiǎn jiǎnchá','Inspect the weld points','weldcheck',[C('weldcheck','Контроль сварочных точек','焊点检查','hàndiǎn jiǎnchá','Weld-point inspection'),C('clearcoat','Нанесение лака','清漆喷涂','qīngqī pēntú','Clearcoat spray'),C('handover','Выдача клиенту','车辆交付','chēliàng jiāofù','Vehicle handover')],'weld-inspect')
    ]},
    {id:'paint',n:3,title:'Окраска',zh:'涂装',py:'túzhuāng',en:'Paint Shop',copy:'BIW проходит подготовку поверхности, электрофорез и нанесение лакокрасочного покрытия.',operations:[
      CH('pretreat','Запустите подготовку поверхности','前处理','qián chǔlǐ','Run surface pretreatment','pretreat',[C('pretreat','Подготовка поверхности','前处理','qián chǔlǐ','Pretreatment'),C('fixture','Фиксация в оснастке','夹具定位','jiājù dìngwèi','Fixture locating'),C('delivery','Доставка дилеру','经销商运输','jīngxiāoshāng yùnshū','Dealer transport')],'pretreatment'),
      CH('ecoat','Погрузите кузов в электрофорезную ванну','电泳','diànyǒng','Apply the e-coat','ecoat',[C('ecoat','Электрофорез','电泳','diànyǒng','E-coat'),C('press','Штамповка панели','冲压成形','chōngyā chéngxíng','Panel stamping'),C('torque','Контроль момента','扭矩检查','niǔjǔ jiǎnchá','Torque check')],'ecoat'),
      CH('spray','Нанесите базовое покрытие и лак','喷涂','pēntú','Spray basecoat and clearcoat','spray',[C('spray','Распылительная система','喷涂系统','pēntú xìtǒng','Spray system'),C('weldgun','Сварочные клещи','焊钳','hànqián','Welding gun'),C('water','Камера дождевого теста','淋雨房','línyǔ fáng','Water-test booth')],'paint-spray')
    ]},
    {id:'assembly',n:4,title:'Финальная сборка',zh:'总装',py:'zǒngzhuāng',en:'Final Assembly',copy:'Окрашенный кузов получает силовой агрегат, стекло, интерьер, светотехнику и колёса.',operations:[
      CH('marriage','Установите силовой агрегат в автомобиль','动力总成装配','dònglì zǒngchéng zhuāngpèi','Install the powertrain','hoist',[C('hoist','Подъёмник силового агрегата','动力总成举升机','dònglì zǒngchéng jǔshēngjī','Powertrain lift'),C('press','Пресс','压力机','yālìjī','Press'),C('spray','Краскопульт','喷枪','pēnqiāng','Spray gun')],'powertrain-marriage'),
      CH('glass','Установите лобовое стекло','玻璃安装','bōli ānzhuāng','Install the windshield','vacuum',[C('vacuum','Вакуумный манипулятор','真空机械手','zhēnkōng jīxièshǒu','Vacuum manipulator'),C('weldgun','Сварочные клещи','焊钳','hànqián','Welding gun'),C('roller','Роликовый стенд','滚筒试验台','gǔntǒng shìyàntái','Roller test bench')],'glass-install'),
      CH('wheel','Затяните крепёж колёс с заданным моментом','车轮拧紧','chēlún nǐngjǐn','Torque the wheel fasteners','torque',[C('torque','Гайковёрт с контролем момента','定扭工具','dìngniǔ gōngjù','Torque-controlled nutrunner'),C('paintbooth','Окрасочная камера','喷漆室','pēnqī shì','Paint booth'),C('pdi','PDI-лист','交付检查表','jiāofù jiǎnchá biǎo','PDI checklist')],'wheel-torque')
    ]},
    {id:'quality',n:5,title:'Качество и испытания',zh:'质量与试验',py:'zhìliàng yǔ shìyàn',en:'Quality & Testing',copy:'Готовый автомобиль проходит геометрию, функциональные проверки и испытания перед выпуском.',operations:[
      CH('gap','Проверьте зазор и перепад поверхностей','间隙面差检查','jiànxì miànchā jiǎnchá','Check gap and flush','gap',[C('gap','Шаблон / измеритель зазора','间隙规','jiànxì guī','Gap gauge'),C('feeder','Подача листа','板料送料','bǎnliào sòngliào','Blank feed'),C('spray','Распылитель','喷枪','pēnqiāng','Spray gun')],'gap-scan'),
      CH('function','Запустите функциональную диагностику','功能测试','gōngnéng cèshì','Run the functional test','scanner',[C('scanner','Диагностический тестер','诊断仪','zhěnduànyí','Diagnostic tester'),C('diecheck','Контроль штампа','模具检查','mújù jiǎnchá','Die inspection'),C('weldgun','Сварочные клещи','焊钳','hànqián','Welding gun')],'functional-test'),
      CH('water','Проведите испытание на герметичность','淋雨测试','línyǔ cèshì','Run the water-leak test','water',[C('water','Дождевой стенд','淋雨试验台','línyǔ shìyàntái','Water-test booth'),C('hoist','Подъёмник двигателя','发动机举升机','fādòngjī jǔshēngjī','Engine lift'),C('paintbooth','Камера окраски','喷漆室','pēnqī shì','Paint booth')],'water-test')
    ]},
    {id:'dealer',n:6,title:'Дилер и передача автомобиля',zh:'经销商交付',py:'jīngxiāoshāng jiāofù',en:'Dealer Delivery',copy:'После выпуска автомобиль поступает к дилеру, проходит PDI и готовится к передаче клиенту.',operations:[
      CH('receive','Примите автомобиль после транспортировки','车辆接收','chēliàng jiēshōu','Receive the transported vehicle','receive',[C('receive','Приёмка автомобиля','车辆接收','chēliàng jiēshōu','Vehicle receipt'),C('ecoat','Электрофорез','电泳','diànyǒng','E-coat'),C('fixture','Сварочная оснастка','焊装夹具','hànzhuāng jiājù','Welding fixture')],'dealer-receive'),
      CH('pdi','Выполните предпродажную проверку','交付前检查','jiāofù qián jiǎnchá','Perform the pre-delivery inspection','pdi',[C('pdi','PDI / предпродажная проверка','交付前检查','jiāofù qián jiǎnchá','Pre-delivery inspection'),C('press','Рабочий цикл пресса','压力机循环','yālìjī xúnhuán','Press cycle'),C('spot','Точечная сварка','点焊','diǎnhàn','Spot welding')],'pdi'),
      CH('handover','Подготовьте автомобиль к передаче клиенту','车辆交付','chēliàng jiāofù','Prepare the vehicle for customer handover','handover',[C('handover','Передача автомобиля','车辆交付','chēliàng jiāofù','Vehicle handover'),C('spray','Окраска','喷涂','pēntú','Paint spraying'),C('gap','Контроль зазора','间隙检查','jiànxì jiǎnchá','Gap inspection')],'handover')
    ]}
  ]);

  let session=null,observer=null,pending=false;
  function languageFor(){const l=app().language;return l==='english'?'english':'chinese'}
  function effectiveLanguage(){if(!session)return'chinese';if(session.language!=='mixed')return session.language;return ((session.stage*3+session.op)%2)?'english':'chinese'}
  function contentLine(op){const l=effectiveLanguage();return l==='english'?'<b>'+esc(op.en)+'</b><em>'+esc(op.ru)+'</em>':'<b>'+esc(op.zh)+'</b><i>'+esc(op.py)+'</i><em>'+esc(op.ru)+'</em>'}
  function choiceLine(c){const l=effectiveLanguage();return l==='english'?'<b>'+esc(c.en)+'</b><small>'+esc(c.ru)+'</small>':'<b>'+esc(c.zh)+'</b><i>'+esc(c.py)+'</i><small>'+esc(c.ru)+'</small>'}
  function vehicleName(){return session&&session.vehicle==='truck'?'Тяжёлый грузовик · SHACMAN-class':'Легковой автомобиль'}

  function sceneHtml(){return '<div class="fps-scene" id="fpsScene"><div class="fps-factory-bg"><i></i><i></i><i></i><i></i></div><div class="fps-conveyor"><i></i><i></i><i></i><i></i><i></i></div><div class="fps-product"><span class="fps-car-roof"></span><span class="fps-car-body"></span><span class="fps-truck-cab"></span><span class="fps-truck-frame"></span><i class="w w1"></i><i class="w w2"></i><i class="w w3"></i></div><div class="fps-press"><span></span><b></b><i></i></div><div class="fps-weld-robot r1"><span></span><b></b><i></i></div><div class="fps-weld-robot r2"><span></span><b></b><i></i></div><div class="fps-weld-sparks">'+Array.from({length:10},(_,i)=>'<i style="--i:'+i+'"></i>').join('')+'</div><div class="fps-paint"><b class="p1"></b><b class="p2"></b><i class="m1"></i><i class="m2"></i></div><div class="fps-hoist"><span></span><i></i><b></b></div><div class="fps-quality"><span></span><i></i><b></b></div><div class="fps-water"><i></i><i></i><i></i><i></i><i></i></div><div class="fps-dealer"><span>MGC AUTO</span><b></b><i></i></div><div class="fps-status" id="fpsSceneStatus">READY</div></div>'}
  function railHtml(){return STAGES.map((s,i)=>'<button type="button" data-fps-stage="'+i+'" class="fps-stage '+(i===session.stage?'active ':'')+(i<session.stage?'done ':'')+'" '+(i>session.stage?'disabled':'')+'><span>0'+s.n+'</span><b>'+esc(s.title)+'</b><small>'+esc(s.zh)+' · '+esc(s.en)+'</small></button>').join('')}
  function operation(){return STAGES[session.stage].operations[session.op]}
  function renderTask(){
    const stage=STAGES[session.stage],op=operation(),task=q('#fpsTask'),choices=q('#fpsChoices'),scene=q('#fpsScene'),status=q('#fpsSceneStatus');if(!task||!choices)return;
    if(scene){scene.dataset.stage=stage.id;scene.dataset.operation=op.visual;scene.dataset.vehicle=session.vehicle;scene.classList.remove('working','success','error')}
    if(status)status.textContent='STATION READY';
    task.innerHTML='<span>ОПЕРАЦИЯ '+(session.op+1)+' / '+stage.operations.length+'</span><h2>'+esc(stage.title)+'</h2><div class="fps-learning">'+contentLine(op)+'</div><p>'+esc(op.ru)+'</p>';
    choices.innerHTML=op.choices.map(c=>'<button type="button" data-fps-choice="'+esc(c.id)+'">'+choiceLine(c)+'</button>').join('');
    qa('[data-fps-choice]',choices).forEach(b=>b.onclick=()=>answer(b.dataset.fpsChoice,b));
    q('#fpsProgress').textContent=(session.stage*3+session.op)+' / 18';q('#fpsProgressBar').style.width=((session.stage*3+session.op)/18*100)+'%';
    q('#fpsStageRail').innerHTML=railHtml();qa('[data-fps-stage]').forEach(b=>b.onclick=()=>{const i=Number(b.dataset.fpsStage);if(i<=session.stage){session.stage=i;session.op=0;renderTask()}});
    q('#fpsStageCopy').innerHTML='<b>'+esc(stage.zh)+' · '+esc(stage.py)+' · '+esc(stage.en)+'</b><span>'+esc(stage.copy)+'</span>';
  }
  function answer(id,button){
    if(!session||session.locked)return;const op=operation(),scene=q('#fpsScene'),status=q('#fpsSceneStatus');session.locked=true;
    if(id!==op.correct){session.errors++;button.classList.add('wrong');if(scene){scene.classList.add('error')}if(status)status.textContent='TRY AGAIN';root.setTimeout(()=>{button.classList.remove('wrong');if(scene)scene.classList.remove('error');session.locked=false},650);return}
    button.classList.add('correct');if(scene){scene.classList.add('working');root.setTimeout(()=>scene.classList.add('success'),500)}if(status)status.textContent='OPERATION RUNNING';
    root.setTimeout(()=>{session.completed++;session.locked=false;if(session.op<2){session.op++;renderTask();return}if(session.stage<STAGES.length-1){showStageComplete()}else showFinish()},1350);
  }
  function showStageComplete(){const stage=STAGES[session.stage],task=q('#fpsTask'),choices=q('#fpsChoices'),status=q('#fpsSceneStatus');if(status)status.textContent='STAGE COMPLETE';task.innerHTML='<span>ЭТАП '+stage.n+' / 6 ЗАВЕРШЁН</span><h2>'+esc(stage.title)+' · готово</h2><div class="fps-stage-success"><b>'+esc(stage.zh)+'</b><i>'+esc(stage.py)+'</i><em>'+esc(stage.en)+'</em></div><p>Изделие перемещается на следующий участок производственного маршрута.</p>';choices.innerHTML='<button class="fps-next primary" id="fpsNextStage">Следующий этап →</button>';q('#fpsNextStage').onclick=()=>{session.stage++;session.op=0;renderTask()};q('#fpsProgress').textContent=(session.stage*3+3)+' / 18';q('#fpsProgressBar').style.width=((session.stage*3+3)/18*100)+'%';q('#fpsStageRail').innerHTML=railHtml()}
  function showFinish(){const main=q('#main');if(!main)return;const name=vehicleName();main.innerHTML='<section class="fps-finish"><div class="fps-finish-vehicle '+(session.vehicle==='truck'?'truck':'car')+'"><i></i><b></b><span></span></div><span>MGC · FACTORY PROCESS SIMULATOR</span><h1>Полный производственный цикл пройден</h1><p>'+esc(name)+' прошёл путь от листовой стали до дилера.</p><div class="fps-finish-route">'+STAGES.map(s=>'<b>'+esc(s.zh)+'<small>'+esc(s.en)+'</small></b>').join('<i>→</i>')+'</div><div class="fps-finish-stats"><b>18 / 18<small>операций</small></b><b>6 / 6<small>этапов</small></b><b>'+session.errors+'<small>ошибок</small></b></div><div class="fps-finish-actions"><button id="fpsReplay" class="primary">Пройти ещё раз</button><button id="fpsBack" class="ghost">← К играм</button></div></section>';q('#fpsReplay').onclick=()=>openSimulator(session.vehicle);q('#fpsBack').onclick=backToGames}
  function backToGames(){session=null;const nav=q('[data-view="games"]');if(nav)nav.click()}
  function openSimulator(vehicle){
    const main=q('#main');if(!main)return;session={vehicle:vehicle==='truck'?'truck':'car',language:languageFor(),stage:0,op:0,completed:0,errors:0,locked:false};
    main.innerHTML='<section class="fps-shell"><header class="fps-head"><div><span>MGC · FACTORY PROCESS SIMULATOR</span><h1>От листа стали до дилера</h1><p>Интерактивный производственный маршрут: штамповка → сварка → окраска → сборка → испытания → дилер.</p></div><button id="fpsClose" class="ghost">← Игры</button></header><div class="fps-controls"><div class="fps-switch"><button data-fps-vehicle="car" class="'+(session.vehicle==='car'?'active':'')+'">Легковой</button><button data-fps-vehicle="truck" class="'+(session.vehicle==='truck'?'active':'')+'">Грузовик</button></div><div class="fps-switch"><button data-fps-lang="chinese" class="'+(session.language==='chinese'?'active':'')+'">中文 + Pinyin</button><button data-fps-lang="english" class="'+(session.language==='english'?'active':'')+'">English</button><button data-fps-lang="mixed">Mixed</button></div></div><div class="fps-progress"><span id="fpsProgress">0 / 18</span><i><b id="fpsProgressBar"></b></i></div><div class="fps-route" id="fpsStageRail"></div><div class="fps-workspace"><aside class="fps-task" id="fpsTask"></aside><article class="fps-visual">'+sceneHtml()+'<div class="fps-stage-copy" id="fpsStageCopy"></div></article><aside class="fps-choices" id="fpsChoices"></aside></div></section>';
    q('#fpsClose').onclick=backToGames;qa('[data-fps-lang]').forEach(b=>b.onclick=()=>{session.language=b.dataset.fpsLang;qa('[data-fps-lang]').forEach(x=>x.classList.toggle('active',x===b));renderTask()});qa('[data-fps-vehicle]').forEach(b=>b.onclick=()=>{session.vehicle=b.dataset.fpsVehicle;qa('[data-fps-vehicle]').forEach(x=>x.classList.toggle('active',x===b));renderTask()});renderTask();
  }
  function injectEntry(){
    if(app().view!=='games'||app().gameSession)return;const main=q('#main'),grid=main&&q('.game-grid',main);if(!grid||q('.factory-process-entry',main))return;
    const wrap=root.document.createElement('section');wrap.className='factory-process-entry';wrap.innerHTML='<div class="section-title"><div><span class="kicker">FACTORY PROCESS SIMULATOR · SPECIAL GAME</span><h2>Пройдите весь автомобильный завод</h2><p>18 операций от штамповки до дилера. Выполняйте реальные производственные действия и учите китайский или английский прямо в процессе.</p></div></div><div class="fps-entry-grid"><button data-fps-open="car"><span>Легковой автомобиль</span><h3>От листа стали до дилера</h3><p>Штамповка → сварка → окраска → сборка → Quality → дилер</p><b>Начать маршрут →</b></button><button data-fps-open="truck"><span>Тяжёлый грузовик · SHACMAN-class</span><h3>Производственный маршрут грузовика</h3><p>Тот же цикл с грузовой визуальной моделью и производственным контекстом.</p><b>Начать маршрут →</b></button></div>';
    grid.parentNode.insertBefore(wrap,grid.nextSibling);qa('[data-fps-open]',wrap).forEach(b=>b.onclick=()=>openSimulator(b.dataset.fpsOpen));
  }
  function schedule(){if(pending)return;pending=true;root.requestAnimationFrame(()=>{pending=false;injectEntry()})}
  function install(){injectEntry();observer=new MutationObserver(schedule);observer.observe(root.document.body,{subtree:true,childList:true})}
  frontend.register('factory-process-simulator-v630',{install,open:openSimulator,stages:STAGES,totalOperations:18});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
