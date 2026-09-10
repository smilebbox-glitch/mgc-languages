/* v6.0.35 — explicit 3D learning lab, independent from legacy game routes. */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend)return;
  if(frontend.has&&frontend.has('three-d-lab-v635'))return;

  const DATA={
    car:[
      {id:'bumper',ru:'Передний бампер',zh:'前保险杠',py:'qián bǎoxiǎnggàng',en:'front bumper',x:286,y:103},
      {id:'hood',ru:'Капот',zh:'发动机盖',py:'fādòngjī gài',en:'hood',x:246,y:82},
      {id:'windshield',ru:'Лобовое стекло',zh:'挡风玻璃',py:'dǎngfēng bōli',en:'windshield',x:210,y:60},
      {id:'mirror',ru:'Наружное зеркало',zh:'后视镜',py:'hòushìjìng',en:'side mirror',x:235,y:88},
      {id:'door',ru:'Дверь',zh:'车门',py:'chēmén',en:'door',x:178,y:103},
      {id:'fender',ru:'Переднее крыло',zh:'前翼子板',py:'qián yìzǐbǎn',en:'front fender',x:250,y:118},
      {id:'headlamp',ru:'Фара',zh:'前照灯',py:'qiánzhàodēng',en:'headlamp',x:300,y:92},
      {id:'wheel',ru:'Колесо',zh:'车轮',py:'chēlún',en:'wheel',x:270,y:145}
    ],
    truck:[
      {id:'cab',ru:'Кабина',zh:'驾驶室',py:'jiàshǐshì',en:'cab',x:270,y:66},
      {id:'grille',ru:'Решётка радиатора',zh:'散热器格栅',py:'sànrèqì géshān',en:'radiator grille',x:312,y:91},
      {id:'bumper',ru:'Передний бампер',zh:'前保险杠',py:'qián bǎoxiǎnggàng',en:'front bumper',x:314,y:122},
      {id:'headlamp',ru:'Фара',zh:'前照灯',py:'qiánzhàodēng',en:'headlamp',x:298,y:80},
      {id:'fuel',ru:'Топливный бак',zh:'燃油箱',py:'rányóuxiāng',en:'fuel tank',x:190,y:122},
      {id:'fifth',ru:'Седельно-сцепное устройство',zh:'第五轮',py:'dìwǔlún',en:'fifth wheel',x:154,y:92},
      {id:'axle',ru:'Ведущая ось',zh:'驱动桥',py:'qūdòngqiáo',en:'drive axle',x:108,y:138},
      {id:'wheel',ru:'Колесо',zh:'车轮',py:'chēlún',en:'wheel',x:82,y:152}
    ]
  };

  let mode='car', yaw=-18, pitch=-8, installed=false;
  function q(s,scope){return (scope||document).querySelector(s)}
  function qa(s,scope){return Array.from((scope||document).querySelectorAll(s))}
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]))}

  function installNav(){
    const sidebar=q('#sidebar');if(!sidebar||q('[data-v635-open]',sidebar))return;
    const games=q('[data-view="games"]',sidebar);if(!games)return;
    const btn=document.createElement('button');
    btn.type='button';btn.className='nav-item v635-3d-nav';btn.dataset.v635Open='1';
    btn.innerHTML='<span>3D</span>3D тренажёр';
    games.insertAdjacentElement('afterend',btn);
  }

  function modelMarkup(){
    const truck=mode==='truck';
    return '<div class="v635-model '+(truck?'v635-truck':'v635-car')+'" data-v635-model>'+
      '<div class="v635-body"></div><div class="v635-cabin"></div>'+(truck?'<div class="v635-bed"></div>':'')+
      '<div class="v635-wheel w1"></div><div class="v635-wheel w2"></div>'+(truck?'<div class="v635-wheel w3"></div>':'')+
      DATA[mode].map(p=>'<button type="button" class="v635-part-dot" data-v635-part="'+p.id+'" style="left:'+p.x+'px;top:'+p.y+'px" aria-label="'+esc(p.ru)+'"></button>').join('')+
      '</div>';
  }

  function listMarkup(){
    return DATA[mode].map((p,i)=>'<button type="button" data-v635-part="'+p.id+'"'+(i===0?' class="active"':'')+'><span><b>'+esc(p.ru)+'</b><small>'+esc(p.en)+'</small></span><small>'+esc(p.zh)+'</small></button>').join('');
  }

  function render(){
    const main=q('#main');if(!main)return;
    const first=DATA[mode][0];
    main.innerHTML='<section class="v635-3d-shell">'+
      '<header class="v635-3d-head"><div><div class="kicker">MGC · 3D LANGUAGE TRAINING</div><h1>3D тренажёр автомобиля</h1><p>Поворачивайте модель мышкой или пальцем и выбирайте узлы. Термин сразу показывается на русском, китайском, pinyin и английском.</p></div><div class="v635-3d-tabs"><button type="button" data-v635-mode="car"'+(mode==='car'?' class="active"':'')+'>Легковой автомобиль</button><button type="button" data-v635-mode="truck"'+(mode==='truck'?' class="active"':'')+'>Грузовой автомобиль</button></div></header>'+
      '<div class="v635-3d-card"><div class="v635-3d-stage-wrap"><div class="v635-3d-stage" data-v635-stage>'+modelMarkup()+'</div><div class="v635-webgl-note">Интерактивный 3D режим · drag to rotate</div></div>'+
      '<aside class="v635-side"><h3>Узлы автомобиля</h3><p>Нажмите на точку модели или выберите термин из списка.</p><div class="v635-part-list">'+listMarkup()+'</div><div class="v635-3d-info" data-v635-info><strong>'+esc(first.zh)+'</strong><em>'+esc(first.py)+'</em><span>'+esc(first.ru)+' · '+esc(first.en)+'</span></div></aside></div></section>';
    bindStage();selectPart(first.id);
    qa('.nav-item').forEach(n=>n.classList.remove('active'));
    const nav=q('[data-v635-open]');if(nav)nav.classList.add('active');
  }

  function selectPart(id){
    const p=DATA[mode].find(x=>x.id===id)||DATA[mode][0];
    qa('[data-v635-part]').forEach(n=>n.classList.toggle('active',n.dataset.v635Part===p.id));
    const info=q('[data-v635-info]');if(info)info.innerHTML='<strong>'+esc(p.zh)+'</strong><em>'+esc(p.py)+'</em><span>'+esc(p.ru)+' · '+esc(p.en)+'</span>';
  }

  function applyRotation(){
    const model=q('[data-v635-model]');if(model)model.style.transform='rotateX('+pitch+'deg) rotateY('+yaw+'deg)';
  }

  function bindStage(){
    const stage=q('[data-v635-stage]');if(!stage)return;
    let drag=false,lastX=0,lastY=0;
    stage.addEventListener('pointerdown',e=>{if(e.target.closest('[data-v635-part]'))return;drag=true;lastX=e.clientX;lastY=e.clientY;stage.setPointerCapture&&stage.setPointerCapture(e.pointerId)});
    stage.addEventListener('pointermove',e=>{if(!drag)return;yaw=Math.max(-65,Math.min(65,yaw+(e.clientX-lastX)*.35));pitch=Math.max(-22,Math.min(12,pitch-(e.clientY-lastY)*.20));lastX=e.clientX;lastY=e.clientY;applyRotation()});
    const stop=()=>{drag=false};stage.addEventListener('pointerup',stop);stage.addEventListener('pointercancel',stop);
  }

  function onClick(e){
    const open=e.target.closest('[data-v635-open]');if(open){e.preventDefault();e.stopImmediatePropagation();render();return}
    const tab=e.target.closest('[data-v635-mode]');if(tab){mode=tab.dataset.v635Mode==='truck'?'truck':'car';yaw=-18;pitch=-8;render();return}
    const part=e.target.closest('[data-v635-part]');if(part&&q('.v635-3d-shell')){selectPart(part.dataset.v635Part);return}
    const normal=e.target.closest('[data-view]');if(normal&&q('.v635-3d-shell')){const nav=q('[data-v635-open]');if(nav)nav.classList.remove('active')}
  }

  function install(){
    if(installed)return;installed=true;installNav();
    document.addEventListener('click',onClick,true);
    new MutationObserver(()=>installNav()).observe(document.documentElement,{subtree:true,childList:true});
  }

  if(frontend.register)frontend.register('three-d-lab-v635',{install:install,open:render});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
