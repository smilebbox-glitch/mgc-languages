/* v6.0.31 — PWA + Mobile Experience Upgrade.
 * Responsive navigation, install guidance, online/offline state, viewport handling and simulator focus mode.
 * Presentation/navigation only: no API, XP, scoring or user-data persistence beyond local UI preferences.
 */
(function(root){
  'use strict';
  const doc=root.document;
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('mobile-web-v631'))return;

  const q=(s,x)=>(x||doc).querySelector(s);
  const qa=(s,x)=>Array.from((x||doc).querySelectorAll(s));
  const coarse=()=>root.matchMedia&&root.matchMedia('(pointer:coarse)').matches;
  const compact=()=>root.matchMedia&&root.matchMedia('(max-width:900px)').matches;
  const standalone=()=>!!((root.matchMedia&&root.matchMedia('(display-mode: standalone)').matches)||root.navigator.standalone===true);
  const SIM_SELECTOR='.ab-shell,.ptb-shell,.fps-shell,.f2-shell,.fti-shell,.fdt-shell';
  let installPrompt=null,observer=null,routeApplied=false,lastDialogFocus=null;

  function emit(name,detail){doc.dispatchEvent(new CustomEvent(name,{detail:detail||{}}))}
  function mobileMode(){return compact()||coarse()||standalone()}

  function setViewport(){
    const vv=root.visualViewport;
    const h=vv?vv.height:root.innerHeight;
    doc.documentElement.style.setProperty('--mgc-viewport-h',Math.max(320,Math.round(h))+'px');
    const keyboard=!!(vv&&root.innerHeight>0&&vv.height/root.innerHeight<.72);
    doc.documentElement.classList.toggle('mgc-keyboard-open',keyboard);
  }

  function markEnvironment(){
    doc.documentElement.classList.toggle('mgc-mobile-web',mobileMode());
    doc.documentElement.classList.toggle('pwa-standalone',standalone());
  }

  function proxyView(view){
    const target=q('.sidebar [data-view="'+view+'"],.topbar [data-view="'+view+'"]');
    if(target){target.click();return true}
    return false;
  }

  function buildDock(){
    const app=q('#appView');
    if(!app||q('#mgcMobileDock'))return;
    const nav=doc.createElement('nav');
    nav.id='mgcMobileDock';nav.className='mgc-mobile-dock';nav.setAttribute('aria-label','Мобильная навигация');
    nav.innerHTML=[
      ['home','⌂','Главная'],['topics','▤','Темы'],['games','◇','Игры'],['roleplay','◉','Сценарии'],['more','☰','Ещё']
    ].map(i=>'<button type="button" data-mobile-view="'+i[0]+'"><span aria-hidden="true">'+i[1]+'</span>'+i[2]+'</button>').join('');
    app.appendChild(nav);
    qa('[data-mobile-view]',nav).forEach(btn=>btn.addEventListener('click',function(){
      const view=btn.dataset.mobileView;
      if(view==='more'){
        const menu=q('#menuToggle');if(menu)menu.click();return;
      }
      proxyView(view);
    }));
    syncDock();
  }

  function syncDock(){
    const dock=q('#mgcMobileDock');if(!dock)return;
    const active=q('.sidebar .nav-item.active[data-view]');
    const view=active&&active.dataset.view;
    qa('[data-mobile-view]',dock).forEach(b=>{
      const selected=b.dataset.mobileView===view;
      b.classList.toggle('active',selected);
      if(selected)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
    });
  }

  function networkPill(){
    let el=q('#mgcNetworkPill');
    if(!el){el=doc.createElement('div');el.id='mgcNetworkPill';el.className='mgc-network-pill';el.setAttribute('role','status');el.setAttribute('aria-live','polite');doc.body.appendChild(el)}
    const online=root.navigator.onLine;
    el.classList.toggle('online',online);el.classList.toggle('offline',!online);
    el.textContent=online?'Подключение восстановлено':'Офлайн · доступна только локальная оболочка';
    if(online){root.setTimeout(()=>{if(root.navigator.onLine)el.classList.add('online')},1500)}
  }

  function closeSheet(){
    const sheet=q('#mgcMobileSheet');
    if(sheet)sheet.remove();
    if(lastDialogFocus&&doc.contains(lastDialogFocus))lastDialogFocus.focus();
    lastDialogFocus=null;
  }

  function openSheet(title,copy,primary){
    closeSheet();
    lastDialogFocus=doc.activeElement;
    const wrap=doc.createElement('div');wrap.id='mgcMobileSheet';wrap.className='mgc-mobile-sheet';
    wrap.innerHTML='<div class="mgc-mobile-sheet-card" role="dialog" aria-modal="true" aria-labelledby="mgcMobileSheetTitle" tabindex="-1"><h3 id="mgcMobileSheetTitle">'+title+'</h3><p>'+copy+'</p><div class="mgc-mobile-sheet-actions">'+(primary||'')+'<button type="button" class="ghost" data-close-sheet>Закрыть</button></div></div>';
    doc.body.appendChild(wrap);
    wrap.addEventListener('click',e=>{if(e.target===wrap||e.target.closest('[data-close-sheet]'))closeSheet()});
    const card=q('.mgc-mobile-sheet-card',wrap);if(card)card.focus();
    return wrap;
  }

  function isIOS(){return /iPad|iPhone|iPod/.test(root.navigator.userAgent)||(root.navigator.platform==='MacIntel'&&root.navigator.maxTouchPoints>1)}
  function isSafari(){return /^((?!chrome|android|crios|fxios).)*safari/i.test(root.navigator.userAgent)}

  function ensureInstallButton(){
    if(standalone()){const old=q('#mgcInstallPill');if(old)old.remove();return}
    const available=!!installPrompt||(isIOS()&&isSafari());
    if(!available||!mobileMode())return;
    let btn=q('#mgcInstallPill');
    if(!btn){btn=doc.createElement('button');btn.id='mgcInstallPill';btn.className='mgc-install-pill';btn.type='button';btn.textContent='Установить MGC';doc.body.appendChild(btn)}
    btn.onclick=async function(){
      if(installPrompt){
        const prompt=installPrompt;installPrompt=null;btn.remove();
        try{await prompt.prompt();await prompt.userChoice}catch(_){}
        return;
      }
      openSheet('Добавить MGC на iPhone','В Safari нажмите «Поделиться», затем выберите «На экран «Домой»». После установки сервис откроется как отдельное приложение.');
    };
  }

  function installPwaHooks(){
    root.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;ensureInstallButton();emit('mgc:pwa-installable',{installable:true})});
    root.addEventListener('appinstalled',()=>{installPrompt=null;const b=q('#mgcInstallPill');if(b)b.remove();doc.documentElement.classList.add('pwa-standalone');emit('mgc:pwa-installed',{installed:true})});
    doc.addEventListener('mgc:pwa-update',()=>{
      openSheet('Обновление готово','Доступна новая версия интерфейса. Если вы не выполняете упражнение прямо сейчас, обновите страницу.', '<button type="button" class="primary" data-update-now>Обновить сейчас</button>');
      const sheet=q('#mgcMobileSheet');const btn=sheet&&q('[data-update-now]',sheet);if(btn)btn.onclick=()=>root.location.reload();
    });
    root.setTimeout(ensureInstallButton,1200);
  }

  function addSceneTools(shell){
    if(!mobileMode()||!shell||shell.dataset.mobileTools==='1')return;
    shell.dataset.mobileTools='1';
    const tools=doc.createElement('div');tools.className='mgc-mobile-scene-tools';
    tools.innerHTML='<button type="button" data-sim-focus aria-pressed="false">⛶ Режим тренажёра</button><button type="button" data-sim-top>↑ К началу</button>';
    const note=doc.createElement('div');note.className='mgc-orientation-note';note.textContent='Для 3D-сцен удобнее альбомная ориентация. Поверните телефон — интерфейс перестроится автоматически.';
    shell.insertBefore(tools,shell.firstChild);shell.insertBefore(note,tools.nextSibling);
    q('[data-sim-focus]',tools).onclick=()=>toggleFocus(shell);
    q('[data-sim-top]',tools).onclick=()=>shell.scrollIntoView({behavior:'smooth',block:'start'});
  }

  function resetFocusMode(){
    qa('.mgc-sim-focused').forEach(shell=>{
      shell.classList.remove('mgc-sim-focused');
      const b=q('[data-sim-focus]',shell);if(b){b.textContent='⛶ Режим тренажёра';b.setAttribute('aria-pressed','false')}
    });
    doc.body.classList.remove('mgc-sim-focus');
  }

  function toggleFocus(shell){
    const active=doc.body.classList.contains('mgc-sim-focus')&&shell.classList.contains('mgc-sim-focused');
    resetFocusMode();
    if(!active){
      doc.body.classList.add('mgc-sim-focus');shell.classList.add('mgc-sim-focused');
      const b=q('[data-sim-focus]',shell);if(b){b.textContent='✕ Свернуть тренажёр';b.setAttribute('aria-pressed','true');b.focus()}
    }
  }

  function scanScenes(){qa(SIM_SELECTOR).forEach(addSceneTools)}

  function applyShortcutRoute(){
    if(routeApplied)return;
    const params=new URLSearchParams(root.location.search);const view=params.get('view');
    if(!view)return;
    const app=q('#appView');if(!app||app.classList.contains('hidden'))return;
    if(proxyView(view)){
      routeApplied=true;
      params.delete('view');
      const rest=params.toString();
      root.history.replaceState(null,'',root.location.pathname+(rest?'?'+rest:'')+root.location.hash);
    }
  }

  function observe(){
    if(observer)return;
    observer=new MutationObserver(()=>{syncDock();scanScenes();applyShortcutRoute()});
    observer.observe(doc.body,{subtree:true,childList:true,attributes:true,attributeFilter:['class','aria-expanded']});
  }

  function install(){
    markEnvironment();setViewport();buildDock();networkPill();installPwaHooks();scanScenes();applyShortcutRoute();observe();
    root.addEventListener('resize',()=>{markEnvironment();setViewport();scanScenes()},{passive:true});
    root.addEventListener('orientationchange',()=>root.setTimeout(setViewport,160),{passive:true});
    root.addEventListener('online',networkPill);root.addEventListener('offline',networkPill);
    if(root.visualViewport){root.visualViewport.addEventListener('resize',setViewport,{passive:true});root.visualViewport.addEventListener('scroll',setViewport,{passive:true})}
    doc.addEventListener('click',e=>{const n=e.target.closest('.nav-item[data-view]');if(n)root.setTimeout(syncDock,0)});
    doc.addEventListener('keydown',e=>{
      if(e.key!=='Escape')return;
      if(q('#mgcMobileSheet')){e.preventDefault();closeSheet();return}
      if(doc.body.classList.contains('mgc-sim-focus')){e.preventDefault();resetFocusMode()}
    });
    doc.addEventListener('visibilitychange',()=>{if(doc.visibilityState==='visible'){markEnvironment();setViewport();syncDock()}});
  }

  frontend.register('mobile-web-v631',{install,setViewport,scanScenes,proxyView,resetFocusMode,closeSheet});
  if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
