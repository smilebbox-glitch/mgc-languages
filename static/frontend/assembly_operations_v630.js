/* v6.0.30 — Assembly Operations + Quality Inspection.
 * Presentation/learning addon for Assembly Builder. No API, XP or canonical scoring ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('assembly-operations-v630'))return;
  const q=(s,x)=>(x||root.document).querySelector(s);
  const qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  const QUALITY={
    car:[
      ['front_door','Посадка передней двери','检查前车门安装','jiǎnchá qián chēmén ānzhuāng'],
      ['bumper','Зазор переднего бампера','检查前保险杠间隙','jiǎnchá qián bǎoxiǎnggàng jiànxì'],
      ['wheel','Крепление колеса','确认车轮紧固','quèrèn chēlún jǐngù'],
      ['headlamp','Установка фары','检查前照灯安装','jiǎnchá qiánzhàodēng ānzhuāng'],
      ['windshield','Посадка лобового стекла','检查挡风玻璃安装','jiǎnchá dǎngfēng bōli ānzhuāng']
    ],
    truck:[
      ['cab_door','Посадка двери кабины','检查驾驶室车门','jiǎnchá jiàshǐshì chēmén'],
      ['bumper','Крепление переднего бампера','检查前保险杠紧固','jiǎnchá qián bǎoxiǎnggàng jǐngù'],
      ['fuel_tank','Установка топливного бака','确认燃油箱安装','quèrèn rányóuxiāng ānzhuāng'],
      ['fifth_wheel','Состояние седельно-сцепного устройства','检查鞍座状态','jiǎnchá ānzuò zhuàngtài'],
      ['wheel','Крепление колеса','确认车轮紧固','quèrèn chēlún jǐngù']
    ],
    carInterior:[
      ['seat','Крепление сиденья','检查座椅安装','jiǎnchá zuòyǐ ānzhuāng'],
      ['seatbelt','Ремень безопасности','检查安全带','jiǎnchá ānquándài'],
      ['steering','Установка рулевого колеса','检查方向盘安装','jiǎnchá fāngxiàngpán ānzhuāng'],
      ['cluster','Работа панели приборов','检查仪表盘','jiǎnchá yíbiǎopán'],
      ['start','Кнопка запуска','检查启动按钮','jiǎnchá qǐdòng ànniǔ']
    ],
    truckInterior:[
      ['driver_seat','Крепление водительского сиденья','检查驾驶员座椅','jiǎnchá jiàshǐyuán zuòyǐ'],
      ['seatbelt','Ремень безопасности','检查安全带','jiǎnchá ānquándài'],
      ['steering','Установка рулевого колеса','检查方向盘安装','jiǎnchá fāngxiàngpán ānzhuāng'],
      ['cluster','Панель приборов','检查仪表盘','jiǎnchá yíbiǎopán'],
      ['parking_brake','Стояночный тормоз','检查驻车制动','jiǎnchá zhùchē zhìdòng']
    ]
  };
  const TOOLS={
    car:['Позиционер кузова','Электрический гайковёрт','Захват двери','Контроль фиксации','Ручной позиционер','Вакуумный захват','Оптический контроль','Динамометрический инструмент','Шаблон посадки','Финальная фиксация'],
    truck:['Рамный позиционер','Подъёмный захват','Кабинный манипулятор','Вакуумный захват','Контроль геометрии','Шаблон посадки','Ударный гайковёрт','Оптический контроль','Подъёмник бака','Контроль сцепного устройства'],
    carInterior:['Монтажный захват','Клипсовый инструмент','Динамометрическая отвёртка','Электрический инструмент','Контроль ремня','Позиционер консоли','Разъёмный тестер','Монтажный шаблон','Функциональный тестер','Финальная проверка'],
    truckInterior:['Сиденийный подъёмник','Контроль ремня','Динамометрический инструмент','Электрический тестер','Монтажный шаблон','Контроль стояночного тормоза','Позиционер панели','Диагностический тестер','Монтажный захват','Финальная фиксация']
  };
  let lastProgress=-1,qc=null;

  function modeFromTitle(){const t=(q('.ab-head h1')||{}).textContent||'';if(t.indexOf('кабину грузовика')>=0)return 'truckInterior';if(t.indexOf('салон')>=0)return 'carInterior';if(t.indexOf('грузовик')>=0)return 'truck';return 'car'}
  function installedLabel(){const done=qa('.ab-rail-item.done');const item=done[done.length-1];if(!item)return 'Узел';const b=q('b',item),sm=q('small',item);return {main:(b&&b.textContent)||'Узел',ru:(sm&&sm.textContent)||''}}
  function showOperation(step){const model=q('.ab-model');if(!model||step<1||step>10)return;const old=q('.abop-motion',model);if(old)old.remove();const mode=modeFromTitle(),label=installedLabel(),tool=TOOLS[mode][Math.min(step-1,9)];const box=root.document.createElement('div');box.className='abop-motion';box.innerHTML='<div class="abop-part"><span>PART '+String(step).padStart(2,'0')+'</span><b>'+esc(label.main)+'</b><small>'+esc(label.ru)+'</small></div><div class="abop-tool"><span>OPERATION</span><b>'+esc(tool)+'</b><small>Позиционирование → фиксация → подтверждение</small></div><div class="abop-lock">✓ УСТАНОВЛЕНО</div>';model.appendChild(box);setTimeout(()=>box.classList.add('run'),30);setTimeout(()=>box.classList.add('locked'),720);setTimeout(()=>box.remove(),1900)}
  function watchProgress(){const p=q('#abProgress');if(!p)return;const n=parseInt(p.textContent,10);if(!Number.isFinite(n)||n===lastProgress)return;if(lastProgress>=0&&n>lastProgress)showOperation(n);lastProgress=n}

  function ensureQualityButton(){const card=q('.ab-complete-card'),actions=card&&q('.ab-complete-actions',card);if(!actions||q('#abQuality',actions))return;const b=root.document.createElement('button');b.id='abQuality';b.className='primary abop-quality-button';b.textContent='Контроль качества →';b.onclick=startQuality;actions.insertBefore(b,actions.firstChild)}
  function renderQuality(){const panel=q('#abQualityPanel');if(!panel||!qc)return;const list=QUALITY[qc.mode],task=list[qc.index];if(!task){panel.innerHTML='<div class="abop-qc-complete"><span>MGC · QUALITY RELEASE</span><h3>Контроль качества завершён</h3><p>5 из 5 контрольных точек подтверждены. Собранная модель готова к следующему этапу Factory Journey.</p><b>QUALITY · PASS</b></div>';qa('.ab3d-marker').forEach(x=>x.classList.remove('qc-current','qc-wrong'));return}panel.innerHTML='<span>QUALITY INSPECTION · '+(qc.index+1)+' / 5</span><h3>'+esc(task[1])+'</h3><div class="abop-qc-term"><b>'+esc(task[2])+'</b><em>'+esc(task[3])+'</em></div><p>Поверните ту же собранную 3D-модель и выберите контрольную точку.</p><div class="abop-qc-rail">'+list.map((x,i)=>'<i class="'+(i<qc.index?'done':i===qc.index?'active':'')+'">'+(i+1)+'</i>').join('')+'</div>';qa('.ab3d-marker').forEach(x=>x.classList.toggle('qc-current',x.dataset.zone===task[0]))}
  function startQuality(){const model=q('.ab-model');if(!model)return;const existing=q('#abQualityPanel',model);if(existing)existing.remove();qc={mode:modeFromTitle(),index:0};const panel=root.document.createElement('section');panel.id='abQualityPanel';panel.className='abop-qc-panel';model.appendChild(panel);model.classList.add('abop-quality-active');renderQuality()}
  function markerClick(e){if(!qc)return;const marker=e.target.closest&&e.target.closest('.ab3d-marker');if(!marker)return;e.preventDefault();e.stopPropagation();const task=QUALITY[qc.mode][qc.index];if(!task)return;if(marker.dataset.zone!==task[0]){marker.classList.add('qc-wrong');setTimeout(()=>marker.classList.remove('qc-wrong'),450);return}marker.classList.add('qc-ok');qc.index++;renderQuality()}

  let pending=false;function scan(){if(pending)return;pending=true;root.requestAnimationFrame(()=>{pending=false;if(!q('.ab-shell')){lastProgress=-1;qc=null;return}watchProgress();ensureQualityButton()})}
  function install(){new MutationObserver(scan).observe(root.document.body,{subtree:true,childList:true,characterData:true});root.document.addEventListener('click',markerClick,true);scan()}
  frontend.register('assembly-operations-v630',{install,quality:QUALITY});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
