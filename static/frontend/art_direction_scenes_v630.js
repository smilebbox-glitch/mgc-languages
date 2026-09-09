/* v6.0.30 — Art Direction Stage 2: Scene Realism.
 * Presentation-only visual environments and executive production theatre.
 * Canonical Game Lab continues to own answers, scoring and progression.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('art-direction-scenes-v630')) return;

  const main=root.document.getElementById('main');
  if(!main) return;

  const SCENES=Object.freeze([
    {id:'assembly',title:'Сборочная линия',sub:'Final assembly · station flow'},
    {id:'welding',title:'Сварочная ячейка',sub:'BIW · robot cell · safety'},
    {id:'paint',title:'Окрасочная камера',sub:'Surface · booth · inspection'},
    {id:'logistics',title:'Внутризаводская логистика',sub:'AGV · supermarket · line side'},
    {id:'quality',title:'Метрологический пост',sub:'CMM · tolerance · disposition'},
    {id:'engineering',title:'Инженерный центр',sub:'Drawing · BOM · digital thread'}
  ]);

  function q(sel,scope){return (scope||root.document).querySelector(sel)}
  function qa(sel,scope){return Array.from((scope||root.document).querySelectorAll(sel))}

  function environment(scene){
    const common='<div class="ad2-ceiling"><i></i><i></i><i></i><i></i></div><div class="ad2-floor"><i></i><i></i><i></i></div>';
    if(scene==='assembly') return '<div class="ad2-env ad2-env-assembly">'+common+'<div class="ad2-line-rail"></div><div class="ad2-carrier"><i></i><b></b></div><div class="ad2-torque-drop"><i></i><b>24 Nm</b></div><span class="ad2-zone-sign">ASSEMBLY · STATION 24</span></div>';
    if(scene==='welding') return '<div class="ad2-env ad2-env-welding">'+common+'<div class="ad2-safety-fence"></div><div class="ad2-weld-gantry"><i></i><b></b></div><div class="ad2-weld-curtain"></div><span class="ad2-zone-sign">BODY SHOP · ROBOT CELL</span></div>';
    if(scene==='paint') return '<div class="ad2-env ad2-env-paint">'+common+'<div class="ad2-light-tunnel"><i></i><i></i><i></i><i></i><i></i></div><div class="ad2-spray-rail"><i></i><b></b></div><div class="ad2-airflow"><i></i><i></i><i></i></div><span class="ad2-zone-sign">PAINT BOOTH · INSPECTION</span></div>';
    if(scene==='logistics') return '<div class="ad2-env ad2-env-logistics">'+common+'<div class="ad2-rack left"><i></i><i></i><i></i></div><div class="ad2-rack right"><i></i><i></i><i></i></div><div class="ad2-agv"><i></i><b></b><em>AGV 07</em></div><div class="ad2-aisle"></div><span class="ad2-zone-sign">LOGISTICS · AISLE L3</span></div>';
    if(scene==='quality') return '<div class="ad2-env ad2-env-quality">'+common+'<div class="ad2-cmm-bridge"><i></i><b></b><em></em></div><div class="ad2-granite-table"></div><div class="ad2-inspection-light"></div><span class="ad2-zone-sign">QUALITY LAB · CMM</span></div>';
    return '<div class="ad2-env ad2-env-engineering">'+common+'<div class="ad2-cad-wall"><i></i><b></b><em></em><strong></strong></div><div class="ad2-model-plinth"><i></i><b>REV C</b></div><div class="ad2-thread-line"></div><span class="ad2-zone-sign">ENGINEERING · DIGITAL THREAD</span></div>';
  }

  function detectScene(node){
    if(node.classList.contains('gw30a-assembly')) return 'assembly';
    if(node.classList.contains('gw30a-welding')) return 'welding';
    if(node.classList.contains('gw30a-paint')) return 'paint';
    if(node.classList.contains('gw30a-logistics')) return 'logistics';
    if(node.classList.contains('gw30b-quality')) return 'quality';
    if(node.classList.contains('gw30b-engineering')) return 'engineering';
    return '';
  }

  function decorateProductionScenes(){
    qa('.gw30a-production-scene,.gw30b-production-scene',main).forEach(function(node){
      const scene=detectScene(node);
      if(!scene||q('.ad2-env',node)) return;
      node.dataset.ad2Scene=scene;
      node.insertAdjacentHTML('afterbegin',environment(scene));
      const mark=root.document.createElement('div');
      mark.className='ad2-scene-brand';
      mark.innerHTML='<span>M</span><b>MGC AUTOMOTIVE LEARNING</b>';
      node.appendChild(mark);
    });
  }

  function markKeyScreens(){
    qa('.game-lab-session,.factory-journey-v2-v630,.arcade-mastery-v620',main).forEach(function(node){
      if(q('.ad2-mgc-mark',node)) return;
      const mark=root.document.createElement('div');
      mark.className='ad2-mgc-mark';
      mark.innerHTML='<span>M</span><b>MGC</b><small>PEOPLE · LANGUAGES · AUTOMOTIVE</small>';
      node.appendChild(mark);
    });
  }

  function theatreScene(scene){
    return '<div class="ad2-theatre-world ad2-theatre-'+scene+'">'+environment(scene)+
      '<div class="ad2-theatre-machine">'+
        (scene==='assembly'?'<div class="ad2-theatre-car"><i></i><b></b><em></em></div><div class="ad2-theatre-tool"></div>':'')+
        (scene==='welding'?'<div class="ad2-theatre-biw"></div><div class="ad2-theatre-robot r1"><i></i><b></b></div><div class="ad2-theatre-robot r2"><i></i><b></b></div><span class="ad2-theatre-spark"></span>':'')+
        (scene==='paint'?'<div class="ad2-theatre-body"></div><div class="ad2-theatre-paint-head"><i></i></div><div class="ad2-theatre-scan"></div>':'')+
        (scene==='logistics'?'<div class="ad2-theatre-tugger"><i></i><b></b></div><div class="ad2-theatre-boxes"><i></i><i></i><i></i></div>':'')+
        (scene==='quality'?'<div class="ad2-theatre-part"></div><div class="ad2-theatre-probe"><i></i></div><div class="ad2-theatre-measure"><small>ACTUAL</small><b>25.08</b><em>25.00 ± 0.20 mm</em></div>':'')+
        (scene==='engineering'?'<div class="ad2-theatre-drawing"><i></i><b>Ø12 H7</b></div><div class="ad2-theatre-bom"><b>VEHICLE</b><span>└ BODY</span><span>  └ MODULE</span><strong>    └ COMPONENT</strong></div>':'')+
      '</div></div>';
  }

  function theatreMarkup(){
    const tabs=SCENES.map(function(s,i){return '<button type="button" data-ad2-scene="'+s.id+'" class="'+(i===0?'active':'')+'"><span>0'+(i+1)+'</span><b>'+s.title+'</b><small>'+s.sub+'</small></button>'}).join('');
    return '<section id="mgcProductionTheatre" class="ad2-theatre hidden" aria-hidden="true">'+
      '<header class="ad2-theatre-top"><div><small>MGC · EXECUTIVE PRODUCTION THEATRE</small><b>Производственные сцены</b></div><button type="button" data-ad2-close>Вернуться к презентации ✕</button></header>'+
      '<div class="ad2-theatre-layout"><nav class="ad2-theatre-tabs">'+tabs+'</nav><div class="ad2-theatre-stage" data-ad2-world> '+theatreScene('assembly')+'</div></div></section>';
  }

  function openTheatre(scene){
    const theatre=q('#mgcProductionTheatre');
    if(!theatre) return;
    theatre.classList.remove('hidden');
    theatre.setAttribute('aria-hidden','false');
    setTheatreScene(scene||'assembly');
  }
  function closeTheatre(){
    const theatre=q('#mgcProductionTheatre');
    if(!theatre) return;
    theatre.classList.add('hidden');
    theatre.setAttribute('aria-hidden','true');
  }
  function setTheatreScene(scene){
    if(!SCENES.some(function(s){return s.id===scene})) scene='assembly';
    qa('[data-ad2-scene]').forEach(function(btn){btn.classList.toggle('active',btn.dataset.ad2Scene===scene)});
    const world=q('[data-ad2-world]');
    if(world) world.innerHTML=theatreScene(scene);
  }

  function installTheatre(){
    const showcase=q('#mgcExecutiveShowcase');
    if(!showcase) return;
    if(!q('#mgcProductionTheatre',showcase)) showcase.insertAdjacentHTML('beforeend',theatreMarkup());
    const factoryPanel=q('[data-ad-panel="2"]',showcase);
    const proof=factoryPanel&&q('.mgc-showcase-proof',factoryPanel);
    if(proof&&!q('.ad2-theatre-trigger',proof)){
      const btn=root.document.createElement('button');
      btn.type='button';btn.className='ad2-theatre-trigger';btn.textContent='Показать производственные сцены →';
      btn.onclick=function(){openTheatre('assembly')};proof.appendChild(btn);
    }
    qa('[data-ad2-scene]',showcase).forEach(function(btn){btn.onclick=function(){setTheatreScene(btn.dataset.ad2Scene)}});
    qa('[data-ad2-close]',showcase).forEach(function(btn){btn.onclick=closeTheatre});
  }

  function refresh(){decorateProductionScenes();markKeyScreens();installTheatre()}
  let queued=false;
  function schedule(){
    if(queued) return;queued=true;
    root.requestAnimationFrame(function(){queued=false;refresh()});
  }

  function install(){
    refresh();
    new MutationObserver(schedule).observe(root.document.body,{subtree:true,childList:true});
    root.document.addEventListener('keydown',function(ev){
      const theatre=q('#mgcProductionTheatre');
      if(ev.key==='Escape'&&theatre&&!theatre.classList.contains('hidden')){
        ev.preventDefault();ev.stopImmediatePropagation();closeTheatre();
      }
    },true);
  }

  frontend.register('art-direction-scenes-v630',{install:install,refresh:refresh,openTheatre:openTheatre,closeTheatre:closeTheatre});
  if(root.document.readyState==='loading') root.document.addEventListener('DOMContentLoaded',install,{once:true}); else install();
})(window);
