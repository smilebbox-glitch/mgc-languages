/* v6.0.30 — Production Motion Stage.
 * Visual production-line simulation for Factory Digital Production Thread.
 * Presentation/orchestration only: no answers, scoring, XP, API or unlock ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('production-motion-v630'))return;
  const q=(s,x)=>(x||root.document).querySelector(s);
  const qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const PHASES=Object.freeze({
    biw:{ru:'Сварочная ячейка',op:'Роботы позиционируют кузов и выполняют сварочные точки',zh:'焊装',py:'hànzhuāng',equipment:'WELD CELL · ROBOT'},
    paint:{ru:'Окрасочная камера',op:'Кузов проходит через распылительные головки и световой тоннель',zh:'涂装',py:'túzhuāng',equipment:'PAINT BOOTH · SPRAY'},
    assembly:{ru:'Линия финальной сборки',op:'Компоненты подаются JIS, инструмент фиксирует узлы',zh:'总装',py:'zǒngzhuāng',equipment:'ASSEMBLY · TORQUE'},
    powertrain:{ru:'Установка силового агрегата',op:'Подъёмник позиционирует двигатель и трансмиссию в изделии',zh:'动力总成',py:'dònglì zǒngchéng',equipment:'POWERTRAIN · LIFT'},
    interior:{ru:'Установка интерьера / кабины',op:'Манипулятор подаёт сиденья и внутренние компоненты',zh:'内饰装配',py:'nèishì zhuāngpèi',equipment:'INTERIOR · MANIPULATOR'},
    quality:{ru:'Контроль качества',op:'Сканирующая рамка проверяет геометрию и контрольные точки',zh:'质量检查',py:'zhìliàng jiǎnchá',equipment:'QUALITY · SCAN'},
    release:{ru:'Сход с линии',op:'Финальный световой контроль и выпуск готового автомобиля',zh:'下线',py:'xiàxiàn',equipment:'EOL · RELEASE'}
  });
  let observer=null,scheduled=false,playing=false,timer=0,lastPhase='';
  const reduced=()=>!!(root.matchMedia&&root.matchMedia('(prefers-reduced-motion: reduce)').matches);

  function sceneMarkup(){
    return '<div class="fpm-scene" aria-hidden="true">'+
      '<div class="fpm-ceiling"><i></i><i></i><i></i><i></i></div>'+
      '<div class="fpm-line-floor"><i></i><i></i><i></i><i></i><i></i><i></i></div>'+
      '<div class="fpm-robot fpm-robot-left"><span class="base"></span><span class="arm a1"></span><span class="arm a2"></span><b class="tool"></b></div>'+
      '<div class="fpm-robot fpm-robot-right"><span class="base"></span><span class="arm a1"></span><span class="arm a2"></span><b class="tool"></b></div>'+
      '<div class="fpm-sparks">'+Array.from({length:12},(_,i)=>'<i style="--i:'+i+'"></i>').join('')+'</div>'+
      '<div class="fpm-paint-rig"><span class="rail"></span><b class="head h1"></b><b class="head h2"></b><i class="mist m1"></i><i class="mist m2"></i></div>'+
      '<div class="fpm-assembly-tool"><span></span><b></b><i></i></div>'+
      '<div class="fpm-hoist"><span class="beam"></span><i class="cable c1"></i><i class="cable c2"></i><b class="load"></b></div>'+
      '<div class="fpm-interior-carrier"><span></span><b></b><i></i></div>'+
      '<div class="fpm-quality-gantry"><span class="leg l1"></span><span class="leg l2"></span><b class="beam"></b><i class="scanner"></i></div>'+
      '<div class="fpm-release-gate"><i></i><b></b><span></span></div>'+
      '<div class="fpm-agv"><span>AGV</span><i></i><b></b></div>'+
      '<div class="fpm-part-bin"><i></i><i></i><i></i></div>'+
      '<div class="fpm-flow-arrow a1"></div><div class="fpm-flow-arrow a2"></div><div class="fpm-flow-arrow a3"></div>'+
      '</div>';
  }

  function toolbarMarkup(){
    return '<div class="fpm-toolbar" data-fpm-toolbar>'+
      '<button type="button" class="fpm-play" data-fpm-play>▶ Проиграть доступный маршрут</button>'+
      '<button type="button" class="fpm-stop" data-fpm-stop disabled>■ Стоп</button>'+
      '<span class="fpm-mode">PRODUCTION MOTION · LOCAL SIMULATION</span>'+
      '</div>';
  }

  function hudMarkup(){
    return '<div class="fpm-hud" data-fpm-hud aria-live="polite"><span>ТЕКУЩАЯ СТАНЦИЯ</span><b data-fpm-title></b><em data-fpm-cn></em><small data-fpm-op></small><i data-fpm-equipment></i></div>';
  }

  function syncPhase(host,phase,animate){
    const p=PHASES[phase]||PHASES.biw;
    host.dataset.motionPhase=phase;
    host.classList.remove('fpm-transition','fpm-arrive');
    if(animate&&!reduced()){
      void host.offsetWidth;
      host.classList.add('fpm-transition');
      root.setTimeout(()=>{host.classList.remove('fpm-transition');host.classList.add('fpm-arrive');root.setTimeout(()=>host.classList.remove('fpm-arrive'),560)},760);
    }
    const hud=q('[data-fpm-hud]',host);
    if(hud){
      const t=q('[data-fpm-title]',hud),cn=q('[data-fpm-cn]',hud),op=q('[data-fpm-op]',hud),eq=q('[data-fpm-equipment]',hud);
      if(t)t.textContent=p.ru;if(cn)cn.textContent=p.zh+' · '+p.py;if(op)op.textContent=p.op;if(eq)eq.textContent=p.equipment;
    }
    lastPhase=phase;
  }

  function currentHost(){return q('#fdt3dHost.fdt3d-host')}
  function unlockedButtons(){return qa('[data-fdt-stage].unlocked:not(:disabled)',q('.factory-digital-thread-v630')).filter(Boolean)}
  function stopPlayback(){
    playing=false;if(timer){root.clearTimeout(timer);timer=0}
    const play=q('[data-fpm-play]'),stop=q('[data-fpm-stop]');
    if(play){play.disabled=false;play.textContent='▶ Проиграть доступный маршрут'}
    if(stop)stop.disabled=true;
  }
  function playRoute(){
    if(reduced())return;
    const buttons=unlockedButtons();if(!buttons.length)return;
    stopPlayback();playing=true;
    const play=q('[data-fpm-play]'),stop=q('[data-fpm-stop]');
    if(play){play.disabled=true;play.textContent='Маршрут выполняется…'}if(stop)stop.disabled=false;
    let index=0;
    const step=()=>{
      if(!playing)return;
      if(index>=buttons.length){stopPlayback();const p=q('[data-fpm-play]');if(p)p.textContent='↻ Повторить доступный маршрут';return}
      const b=buttons[index++];if(b&&typeof b.click==='function')b.click();
      timer=root.setTimeout(step,index===buttons.length?1900:1650);
    };
    step();
  }

  function decorate(){
    const section=q('.factory-digital-thread-v630');const host=currentHost();
    if(!section||!host){stopPlayback();return}
    if(!q('.fpm-scene',host))host.insertAdjacentHTML('beforeend',sceneMarkup()+hudMarkup());
    const model=q('.fdt-model',section);
    if(model&&!q('[data-fpm-toolbar]',model)){
      const head=q('.fdt-model-head',model);
      if(head)head.insertAdjacentHTML('afterend',toolbarMarkup());
      const play=q('[data-fpm-play]',model),stop=q('[data-fpm-stop]',model);
      if(play){play.onclick=playRoute;if(reduced()){play.disabled=true;play.textContent='Анимация отключена настройками системы'}}
      if(stop)stop.onclick=stopPlayback;
    }
    const phase=host.dataset.phase||'biw';if(phase!==lastPhase)syncPhase(host,phase,!!lastPhase);else syncPhase(host,phase,false);
    if(!host._fpmObserver){
      host._fpmObserver=new MutationObserver(m=>{m.forEach(x=>{if(x.type==='attributes'&&x.attributeName==='data-phase'){const next=host.dataset.phase||'biw';syncPhase(host,next,next!==lastPhase)}})});
      host._fpmObserver.observe(host,{attributes:true,attributeFilter:['data-phase']});
    }
  }

  function schedule(){if(scheduled)return;scheduled=true;root.requestAnimationFrame(()=>{scheduled=false;decorate()})}
  function install(){
    decorate();observer=new MutationObserver(schedule);observer.observe(root.document.body,{subtree:true,childList:true});
    root.document.addEventListener('click',ev=>{const b=ev.target&&ev.target.closest?ev.target.closest('[data-fdt-stage],[data-fdt-vehicle]'):null;if(b)root.setTimeout(schedule,0)},true);
  }
  frontend.register('production-motion-v630',{install,reconcile:schedule,phases:PHASES,play:playRoute,stop:stopPlayback});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
