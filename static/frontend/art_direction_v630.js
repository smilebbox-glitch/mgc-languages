/* v6.0.30 — Art Direction / Executive Showcase.
 * Presentation-only: no API, XP, scoring or answer submission.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('art-direction-v630')) return;

  const CAR_SVG='<svg viewBox="0 0 760 260" role="img" aria-label="Цифровой автомобиль">'+
    '<defs><linearGradient id="mgcCarPaint" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#79c7f3" stop-opacity=".88"/><stop offset=".48" stop-color="#277fc6" stop-opacity=".74"/><stop offset="1" stop-color="#143f69" stop-opacity=".95"/></linearGradient></defs>'+
    '<path class="vehicle-shell" d="M83 158 C112 133 157 122 204 117 L270 56 C289 38 318 29 350 29 L461 29 C505 29 536 43 566 72 L620 123 C649 126 679 138 699 156 L713 176 C716 188 707 197 692 198 L666 198 C656 159 626 138 588 138 C550 138 520 159 510 198 L248 198 C238 159 208 138 170 138 C132 138 102 159 92 198 L69 198 C55 198 47 189 51 176 Z"/>'+
    '<path class="vehicle-glass" d="M282 62 C298 46 320 39 348 39 L406 39 L410 104 L237 104 Z"/>'+
    '<path class="vehicle-glass" d="M420 39 L461 39 C493 39 518 50 542 74 L572 104 L425 104 Z"/>'+
    '<path class="vehicle-line" d="M239 112 L575 112 M411 41 L417 189 M276 112 L263 189 M568 112 L602 139"/>'+
    '<path class="vehicle-line" d="M77 166 L114 164 M648 145 L697 160 M312 177 L480 177"/>'+
    '<circle class="vehicle-wheel" cx="170" cy="196" r="48"/><circle class="vehicle-rim" cx="170" cy="196" r="25"/>'+
    '<circle class="vehicle-wheel" cx="588" cy="196" r="48"/><circle class="vehicle-rim" cx="588" cy="196" r="25"/>'+
    '<path class="vehicle-light" d="M648 137 L690 154 L667 160 L635 151 Z"/><path class="vehicle-light" d="M91 148 L126 137 L122 154 L78 161 Z"/>'+
    '<path class="vehicle-scan" d="M92 127 L679 127"/>'+
    '</svg>';

  function query(sel,scope){return (scope||document).querySelector(sel)}
  function queryAll(sel,scope){return Array.from((scope||document).querySelectorAll(sel))}

  function injectHeroVisual(){
    const hero=query('.pilot-hero');
    if(!hero||query('.mgc-hero-visual',hero)) return;
    const visual=document.createElement('div');visual.className='mgc-hero-visual';visual.innerHTML=CAR_SVG;
    const floor=document.createElement('div');floor.className='mgc-hero-floor';
    const beacon=document.createElement('div');beacon.className='mgc-hero-beacon';beacon.innerHTML='<i></i><span>DIGITAL VEHICLE · LIVE</span>';
    hero.appendChild(floor);hero.appendChild(visual);hero.appendChild(beacon);
  }

  function injectJourneyVehicle(){
    queryAll('.fj2-car').forEach(function(car){
      if(query('.mgc-art-car-overlay',car)) return;
      const wrap=document.createElement('div');wrap.className='mgc-art-car-overlay';wrap.innerHTML=CAR_SVG;car.appendChild(wrap);
    });
  }

  function showcaseMarkup(){
    return '<section id="mgcExecutiveShowcase" class="mgc-showcase hidden" aria-hidden="true">'+
      '<header class="mgc-showcase-top"><div class="mgc-showcase-brand"><span class="mgc-showcase-monogram">M</span><span><b>MGC Language Lab</b><small>EXECUTIVE SHOWCASE · AUTOMOTIVE LEARNING</small></span></div>'+
      '<nav class="mgc-showcase-nav" aria-label="Разделы презентации"><button data-ad-slide="0" class="active">01 · Продукт</button><button data-ad-slide="1">02 · Обучение</button><button data-ad-slide="2">03 · Завод</button><button data-ad-slide="3">04 · Ценность</button></nav><button class="mgc-showcase-close" data-ad-close>Закрыть ✕</button></header>'+
      '<div class="mgc-showcase-slide active" data-ad-panel="0"><div class="mgc-showcase-copy"><div class="mgc-showcase-kicker">01 · MGC LANGUAGE LAB</div><h1>Языковая подготовка, встроенная в реальность автозавода.</h1><p>Не отдельный словарь и не набор тестов. Единая корпоративная платформа, где сотрудник учит английский или китайский через реальные процессы сборки, сварки, окраски, логистики, качества и инженерии.</p><div class="mgc-showcase-proof"><span>2029 терминов / язык</span><span>20 Automotive Arcade игр</span><span>Factory Journey 2.0</span><span>Курс 30 дней</span><span>Chinese + Pinyin</span></div><div class="mgc-showcase-quote"><strong>语言连接人与技术</strong><span>yǔyán liánjiē rén yǔ jìshù</span><small>Язык соединяет людей и технологии.</small></div></div><div class="mgc-showcase-visual"><div class="mgc-showcase-car">'+CAR_SVG+'</div><div class="mgc-showcase-flow"><span class="on">SUPPLIER</span><span class="on">LOGISTICS</span><span class="on">WELDING</span><span class="on">PAINT</span><span class="on">ASSEMBLY</span><span class="on">QUALITY</span><span class="on">ENGINEERING</span></div></div></div>'+
      '<div class="mgc-showcase-slide" data-ad-panel="1"><div class="mgc-showcase-copy"><div class="mgc-showcase-kicker">02 · LEARNING ARCHITECTURE</div><h1>От слова — к рабочему решению.</h1><p>Сотрудник проходит последовательность: термин → произношение → фраза → сценарий → игровая операция → производственный инцидент. Интерфейс остаётся русским; изучаемый китайский контент показывается как иероглифы + pinyin + русский смысл.</p><div class="mgc-showcase-proof"><span>A1 → C1 без повторов</span><span>Role Play</span><span>Мини-тесты</span><span>Итоговый экзамен</span><span>AI-помощник</span></div></div><div class="mgc-showcase-visual"><div class="mgc-showcase-process"><article><i>字</i><span><b>Термин</b><small>扭矩 · niǔjǔ · крутящий момент</small></span><em>01</em></article><article><i>话</i><span><b>Рабочая фраза</b><small>请确认扭矩 · qǐng quèrèn niǔjǔ</small></span><em>02</em></article><article><i>场</i><span><b>Сценарий</b><small>Контроль крепежа на станции сборки</small></span><em>03</em></article><article><i>决</i><span><b>Решение</b><small>Выбор действия в реальном производственном контексте</small></span><em>04</em></article></div></div></div>'+
      '<div class="mgc-showcase-slide" data-ad-panel="2"><div class="mgc-showcase-copy"><div class="mgc-showcase-kicker">03 · FACTORY JOURNEY 2.0</div><h1>Обучение как смена на автомобильном заводе.</h1><p>Пользователь проходит семь связанных этапов и решает реальные ситуации: ревизия чертежа, дефицит материала, остановка сварочного робота, дефект окраски, контроль момента, допуск качества и BOM mismatch.</p><div class="mgc-showcase-proof"><span>Digital Vehicle</span><span>Factory Twin</span><span>7 производственных зон</span><span>20 игровых механик</span></div></div><div class="mgc-showcase-visual"><div class="mgc-showcase-car">'+CAR_SVG+'</div><div class="mgc-showcase-process" style="position:absolute;left:5%;right:5%;bottom:5%;padding:0;grid-template-columns:repeat(3,1fr)"><article><i>24</i><span><b>Assembly</b><small>Torque verification</small></span><em>RUN</em></article><article><i>Q</i><span><b>Quality</b><small>Gap tolerance check</small></span><em>READY</em></article><article><i>B</i><span><b>Engineering</b><small>Drawing ↔ BOM revision</small></span><em>WAIT</em></article></div></div></div>'+
      '<div class="mgc-showcase-slide" data-ad-panel="3"><div class="mgc-showcase-copy"><div class="mgc-showcase-kicker">04 · BUSINESS VALUE</div><h1>Платформа, которую можно показать и сотруднику, и руководству.</h1><p>Один продукт объединяет профессиональную лексику, адаптацию сотрудников, реальные производственные сценарии и понятный прогресс. Он подходит для пилота внутри компании и масштабируется без изменения базовой архитектуры обучения.</p><div class="mgc-showcase-proof"><span>Корпоративный SSO</span><span>LAN / PWA</span><span>PostgreSQL</span><span>Ролевой доступ</span><span>Server-side scoring</span></div></div><div class="mgc-showcase-visual"><div class="mgc-showcase-kpi"><article><small>CONTENT</small><b>4 058</b><p>терминов в двух языковых треках</p></article><article><small>ARCADE</small><b>20</b><p>производственных игровых механик</p></article><article><small>JOURNEY</small><b>7</b><p>связанных этапов автомобильного производства</p></article><article><small>SESSION CONTRACT</small><b>5</b><p>ответов за игровую сессию с server-authoritative scoring</p></article></div></div></div>'+
      '</section>';
  }

  let slide=0;
  function setSlide(index){
    slide=Math.max(0,Math.min(3,Number(index)||0));
    queryAll('[data-ad-panel]').forEach(function(p){p.classList.toggle('active',Number(p.dataset.adPanel)===slide)});
    queryAll('[data-ad-slide]').forEach(function(b){b.classList.toggle('active',Number(b.dataset.adSlide)===slide)});
  }
  function openShowcase(){const s=query('#mgcExecutiveShowcase');if(!s)return;s.classList.remove('hidden');s.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';setSlide(0)}
  function closeShowcase(){const s=query('#mgcExecutiveShowcase');if(!s)return;s.classList.add('hidden');s.setAttribute('aria-hidden','true');document.body.style.overflow=''}

  function installShowcase(){
    if(!query('#mgcExecutiveShowcase')) document.body.insertAdjacentHTML('beforeend',showcaseMarkup());
    const top=query('.topbar');
    if(top&&!query('#mgcShowcaseTrigger')){
      const btn=document.createElement('button');btn.id='mgcShowcaseTrigger';btn.type='button';btn.className='mgc-showcase-trigger';btn.textContent='Презентация';btn.title='Открыть executive showcase';
      const profile=query('.pilot-profile',top);top.insertBefore(btn,profile||null);
    }
    const trigger=query('#mgcShowcaseTrigger');if(trigger)trigger.onclick=openShowcase;
    queryAll('[data-ad-close]').forEach(function(b){b.onclick=closeShowcase});
    queryAll('[data-ad-slide]').forEach(function(b){b.onclick=function(){setSlide(Number(b.dataset.adSlide))}});
    document.addEventListener('keydown',function(ev){
      const s=query('#mgcExecutiveShowcase');if(!s||s.classList.contains('hidden')) return;
      if(ev.key==='Escape') closeShowcase();
      if(ev.key==='ArrowRight') setSlide(slide+1);
      if(ev.key==='ArrowLeft') setSlide(slide-1);
    });
  }

  function refresh(){injectHeroVisual();injectJourneyVehicle()}
  function install(){
    installShowcase();refresh();
    const observer=new MutationObserver(function(){refresh()});observer.observe(document.body,{subtree:true,childList:true});
  }

  frontend.register('art-direction-v630',{install:install,refresh:refresh,openShowcase:openShowcase,closeShowcase:closeShowcase});
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',install,{once:true}); else install();
})(window);
