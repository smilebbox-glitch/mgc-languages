/* v6.0.34 — executive clean UI hardening. */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend)return;
  if(frontend.has&&frontend.has('executive-clean-v634'))return;

  const VIEWS=new Set(['home','topics','quiz','roleplay','course30','games','xp','exam','assistant','chinese-basics','notifications','manager','admin']);
  let installed=false;

  function nav(view){
    try{
      if(!frontend.has('navigation'))throw new Error('navigation unavailable');
      return Promise.resolve(frontend.get('navigation').setView(view));
    }catch(err){
      const main=document.getElementById('main');
      if(main)main.innerHTML='<section class="card v633-route-error"><div class="kicker">MGC LANGUAGE LAB</div><h2>Раздел временно недоступен</h2><p>Повторите открытие раздела.</p><button class="primary" data-view="home">На главную</button></section>';
      return Promise.reject(err);
    }
  }

  function normalizeHome(){
    const main=document.getElementById('main');
    if(!main)return;
    const hero=main.querySelector('.pilot-hero');
    if(hero){
      const h1=hero.querySelector('h1');
      const p=hero.querySelector('p');
      if(h1 && /китайск/i.test(h1.textContent||'')) h1.textContent='Китайский для работы в автопроме';
      if(h1 && /english|английск/i.test(h1.textContent||'')) h1.textContent='Английский для работы в автопроме';
      if(p) p.textContent='Профессиональная лексика, рабочие ситуации и короткая практика для производственных команд.';
    }
    const today=main.querySelector('.pilot-next-head h2');
    if(today)today.textContent='Практика на сегодня';
    const sub=main.querySelector('.pilot-next-head p');
    if(sub)sub.textContent='Продолжите с последнего шага или выберите короткое упражнение.';
    const topicTitle=main.querySelector('.pilot-topics .pilot-section-head h2');
    if(topicTitle)topicTitle.textContent='Профессиональные темы';
  }

  function removeRejectedAndDecorative(){
    document.querySelectorAll('[data-start-v618-game="match"],[data-start-game="match"],[data-game-type="match"]').forEach(function(btn){
      const card=btn.closest('.game-lab-card,.game-card,.arcade-card')||btn;
      card.remove();
    });
    document.querySelectorAll('.dv3d-showcase-trigger').forEach(function(btn){btn.remove();});
  }

  function repairCounts(){
    document.querySelectorAll('.game-lab-summary b,.game-lab-head .kicker,.page-head .kicker').forEach(function(el){
      const t=String(el.textContent||'');
      if(/^20$/.test(t.trim()))el.textContent='19';
      else if(/20\s*ИГР/i.test(t))el.textContent=t.replace(/20\s*ИГР/i,'19 ИГР');
    });
  }

  function sweep(){normalizeHome();removeRejectedAndDecorative();repairCounts();}

  function install(){
    if(installed)return;installed=true;
    root.addEventListener('click',function(event){
      const button=event.target&&event.target.closest?event.target.closest('[data-view]'):null;
      if(!button||!button.closest('.sidebar,.topbar'))return;
      const view=String(button.dataset.view||'');
      if(!VIEWS.has(view))return;
      event.preventDefault();
      event.stopImmediatePropagation();
      nav(view).catch(function(){});
    },true);

    sweep();
    let queued=false;
    const observer=new MutationObserver(function(){
      if(queued)return;queued=true;
      root.requestAnimationFrame(function(){queued=false;sweep();});
    });
    observer.observe(document.documentElement,{childList:true,subtree:true});
    document.addEventListener('mgc:frontend-ready',sweep);
  }

  try{frontend.register('executive-clean-v634',{install:install,refresh:sweep});}catch(_){ }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
