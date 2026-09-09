/* v6.0.31 — Factory Training Intelligence.
 * Linked production consequences, simulated KPIs, adaptive next shifts, shift report and local browser TTS.
 * Special training layer only. No API, XP or canonical scoring ownership.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('factory-training-intelligence-v631'))return;
  const q=(s,x)=>(x||root.document).querySelector(s),qa=(s,x)=>Array.from((x||root.document).querySelectorAll(s));
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const PROFILE_KEY='mgc_factory_training_profile_v631';
  const STAGE_ORDER=['stamping','welding','paint','assembly','quality','dealer'];
  const KPI_TERMS={
    fpy:{ru:'FPY · First Pass Yield',zh:'一次合格率',py:'yīcì hégé lǜ',en:'First Pass Yield'},
    rework:{ru:'Доработка',zh:'返修',py:'fǎnxiū',en:'Rework'},
    downtime:{ru:'Простой',zh:'停机时间',py:'tíngjī shíjiān',en:'Downtime'},
    holds:{ru:'Quality Hold',zh:'质量隔离',py:'zhìliàng gélí',en:'Quality Hold'},
    takt:{ru:'Takt Time',zh:'节拍时间',py:'jiépāi shíjiān',en:'Takt Time'},
    cycle:{ru:'Cycle Time',zh:'周期时间',py:'zhōuqī shíjiān',en:'Cycle Time'}
  };
  const CONSEQUENCES={
    stamping:{ru:'Дефект штамповки дошёл до следующего передела: позиционирование панели осложнилось.',zh:'冲压缺陷流入下道工序，零件定位受到影响。',py:'chōngyā quēxiàn liúrù xià dào gōngxù, língjiàn dìngwèi shòudào yǐngxiǎng.',en:'The stamping defect escaped downstream and affected part location.'},
    welding:{ru:'Дефект BIW ушёл дальше по процессу: стоимость последующей доработки выросла.',zh:'焊装缺陷流入后工序，返修成本增加。',py:'hànzhuāng quēxiàn liúrù hòu gōngxù, fǎnxiū chéngběn zēngjiā.',en:'The BIW defect escaped downstream, increasing rework cost.'},
    paint:{ru:'Дефект покрытия дошёл до сборки: требуется поздний rework и дополнительный простой.',zh:'涂装缺陷流入总装，需要后续返修并造成停机。',py:'túzhuāng quēxiàn liúrù zǒngzhuāng, xūyào hòuxù fǎnxiū bìng zàochéng tíngjī.',en:'The paint defect reached assembly, causing late rework and downtime.'},
    assembly:{ru:'Сборочное отклонение обнаружено только на Quality: выпуск изделия заблокирован.',zh:'总装偏差在质量检查阶段才被发现，车辆无法放行。',py:'zǒngzhuāng piānchā zài zhìliàng jiǎnchá jiēduàn cái bèi fāxiàn, chēliàng wúfǎ fàngxíng.',en:'The assembly deviation was detected only at Quality, blocking release.'},
    quality:{ru:'Неисправность прошла Quality и дошла до PDI: риск позднего удержания автомобиля.',zh:'质量问题流入PDI，造成车辆后期隔离风险。',py:'zhìliàng wèntí liúrù PDI, zàochéng chēliàng hòuqī gélí fēngxiǎn.',en:'The quality issue escaped to PDI, creating a late vehicle hold.'},
    dealer:{ru:'Ошибка PDI влияет на готовность автомобиля к передаче клиенту.',zh:'PDI问题影响车辆按时交付。',py:'PDI wèntí yǐngxiǎng chēliàng ànshí jiāofù.',en:'The PDI issue affects on-time customer delivery.'}
  };
  const VOCAB={
    stamping:[['冲压','chōngyā','Stamping'],['起皱','qǐzhòu','Wrinkling'],['开裂','kāiliè','Split']],
    welding:[['焊点','hàndiǎn','Weld point'],['夹具','jiājù','Fixture'],['定位','dìngwèi','Location']],
    paint:[['喷涂','pēntú','Paint spraying'],['流挂','liúguà','Paint sag'],['颗粒','kēlì','Dust nib']],
    assembly:[['扭矩','niǔjǔ','Torque'],['紧固件','jǐngùjiàn','Fastener'],['装配','zhuāngpèi','Assembly']],
    quality:[['间隙','jiànxì','Gap'],['故障码','gùzhàngmǎ','DTC'],['淋雨测试','línyǔ cèshì','Water test']],
    dealer:[['交付前检查','jiāofù qián jiǎnchá','PDI'],['车辆交付','chēliàng jiāofù','Vehicle delivery'],['胎压','tāiyā','Tire pressure']]
  };
  let session=null,timer=null,observer=null,pending=false;

  function app(){try{return frontend.get('app-state').current()}catch(_){return{language:'chinese',view:'games'}}}
  function base(){try{return frontend.get('factory-simulator-stage2-v630')}catch(_){return null}}
  function profile(){
    try{
      const raw=JSON.parse(root.localStorage.getItem(PROFILE_KEY)||'{}');
      return {runs:Number(raw.runs)||0,stageMisses:Object.assign({},raw.stageMisses||{}),termMisses:Object.assign({},raw.termMisses||{}),lastRole:raw.lastRole||'operator'};
    }catch(_){return{runs:0,stageMisses:{},termMisses:{},lastRole:'operator'}}
  }
  function saveProfile(p){try{root.localStorage.setItem(PROFILE_KEY,JSON.stringify(p))}catch(_){}}
  function resetProfile(){try{root.localStorage.removeItem(PROFILE_KEY)}catch(_){}}
  function stageIdx(id){return Math.max(0,STAGE_ORDER.indexOf(id))}
  function stageObject(id){const b=base();return b&&b.stages?b.stages.find(s=>s.id===id):null}
  function roleObject(id){const b=base();return b&&b.roles?b.roles[id]:null}
  function actionObject(id){const b=base();return b&&b.actions?b.actions[id]:null}
  function languageFor(index){
    if(!session)return'chinese';
    if(session.language!=='mixed')return session.language;
    return index%2?'english':'chinese';
  }
  function line(obj,index){
    const l=languageFor(index==null?(session?session.index:0):index);
    if(l==='english')return '<b>'+esc(obj.en||'')+'</b><small>'+esc(obj.ru||'')+'</small>';
    return '<b>'+esc(obj.zh||'')+'</b><i>'+esc(obj.py||'')+'</i><small>'+esc(obj.ru||'')+'</small>';
  }
  function topWeakStages(p,limit){
    return STAGE_ORDER.map(id=>({id,score:Number(p.stageMisses[id])||0})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,limit||3);
  }
  function weakLabel(p){
    const weak=topWeakStages(p,3);
    if(!weak.length)return'Профиль пока чистый — первая смена будет сбалансированной.';
    return 'Адаптивный фокус: '+weak.map(x=>{const s=stageObject(x.id);return s?s.title:x.id}).join(' · ');
  }
  function weightedEvents(){
    const b=base();if(!b||!b.events)return[];
    const p=profile();
    const all=b.events.map((e,i)=>({e,i,weight:1+(Number(p.stageMisses[e.stage])||0)*1.8+Math.random()}));
    const guaranteed=[];
    STAGE_ORDER.forEach(stage=>{
      const pool=all.filter(x=>x.e.stage===stage).sort((a,b)=>b.weight-a.weight);
      if(pool[0])guaranteed.push(pool[0]);
    });
    const used=new Set(guaranteed.map(x=>x.e.id));
    const rest=all.filter(x=>!used.has(x.e.id)).sort((a,b)=>b.weight-a.weight).slice(0,Math.max(0,10-guaranteed.length));
    return guaranteed.concat(rest).map(x=>x.e).sort((a,b)=>stageIdx(a.stage)-stageIdx(b.stage)).slice(0,10);
  }
  function voiceAvailable(){return !!(root.speechSynthesis&&root.SpeechSynthesisUtterance)}
  function bestVoice(lang){
    if(!voiceAvailable())return null;
    const voices=root.speechSynthesis.getVoices?root.speechSynthesis.getVoices():[];
    const isZh=lang==='zh-CN';
    const filtered=voices.filter(v=>String(v.lang||'').toLowerCase().startsWith(isZh?'zh':'en'));
    const hints=isZh?/xiaoxiao|huihui|yaoyao|tingting|mandarin|putonghua|普通话/i:/aria|jenny|guy|samantha|google us english|microsoft/i;
    return filtered.find(v=>v.localService!==false&&hints.test(v.name||''))||filtered.find(v=>v.localService!==false)||filtered[0]||null;
  }
  function speakCurrent(slow){
    if(!session||!voiceAvailable())return;
    const event=session.events[session.index];if(!event)return;
    const l=languageFor(session.index),zh=l!=='english';
    const text=zh?event.dialogue.zh:event.dialogue.en;
    try{
      root.speechSynthesis.cancel();
      const u=new root.SpeechSynthesisUtterance(text);
      u.lang=zh?'zh-CN':'en-US';u.rate=slow?.72:.94;u.pitch=1;u.volume=1;
      const v=bestVoice(u.lang);if(v)u.voice=v;
      root.speechSynthesis.speak(u);
    }catch(_){ }
  }
  function kpiHtml(){
    const k=session.kpi,cycle=Math.round(k.cycleSec);
    return '<div class="fti-kpis">'+
      '<div><span>FPY (сим.)</span><b>'+Math.max(0,Math.round(k.fpy))+'%</b><small>一次合格率 · yīcì hégé lǜ</small></div>'+
      '<div><span>Rework</span><b>'+k.rework+'</b><small>返修 · fǎnxiū</small></div>'+
      '<div><span>Downtime</span><b>'+k.downtime+' min</b><small>停机时间 · tíngjī shíjiān</small></div>'+
      '<div><span>HOLD</span><b>'+k.holds+'</b><small>质量隔离 · zhìliàng gélí</small></div>'+
      '<div><span>Cycle / Takt</span><b>'+cycle+' / '+k.taktSec+' s</b><small>周期时间 / 节拍时间</small></div>'+
    '</div>';
  }
  function setupHtml(){
    const b=base(),p=profile();if(!b)return'<section class="fti-shell"><p>Factory Simulator Stage 2 не загружен.</p></section>';
    return '<section class="fti-shell"><header class="fti-head"><div><span>MGC · FACTORY TRAINING INTELLIGENCE</span><h1>Factory Shift Intelligence</h1><p>Связанные последствия решений, производственные KPI, адаптивная следующая смена и рабочая речь.</p></div><button class="ghost" id="ftiClose">← Игры</button></header>'+
      '<div class="fti-profile"><b>Adaptive profile · run '+(p.runs+1)+'</b><span>'+esc(weakLabel(p))+'</span></div>'+
      '<div class="fti-setup"><section><h2>1. Роль</h2><div class="fti-options">'+Object.keys(b.roles).map(k=>'<button data-fti-role="'+k+'" class="'+(k===p.lastRole?'active':'')+'">'+lineStatic(b.roles[k])+'</button>').join('')+'</div></section>'+
      '<section><h2>2. Объект</h2><div class="fti-options"><button data-fti-vehicle="car" class="active"><b>Легковой автомобиль</b><small>Passenger vehicle</small></button><button data-fti-vehicle="truck"><b>Тяжёлый грузовик</b><small>SHACMAN-class reference</small></button></div></section>'+
      '<section><h2>3. Язык</h2><div class="fti-options"><button data-fti-lang="chinese" class="'+(app().language==='english'?'':'active')+'"><b>中文 + Pinyin</b><small>Русский смысл</small></button><button data-fti-lang="english" class="'+(app().language==='english'?'active':'')+'"><b>English</b><small>Русский смысл</small></button><button data-fti-lang="mixed"><b>Mixed</b><small>中文 / English</small></button></div></section>'+
      '<section><h2>4. Голос</h2><label class="fti-toggle"><input type="checkbox" id="ftiAutoVoice" checked><span>Автоозвучка рабочего диалога</span></label><small>'+(voiceAvailable()?'Системный TTS доступен. Выбирается лучший локальный голос zh-CN / en-US.':'Системный TTS недоступен в этом браузере.')+'</small></section></div>'+
      '<div class="fti-start"><button id="ftiStart">Начать адаптивную смену →</button><button id="ftiReset" class="ghost">Сбросить адаптивный профиль</button></div></section>';
  }
  function lineStatic(obj){return '<b>'+esc(obj.title||obj.ru||'')+'</b><small>'+esc(obj.zh||'')+' · '+esc(obj.py||'')+' · '+esc(obj.en||'')+'</small>'}
  function mapHtml(active){
    const b=base();return '<div class="fti-map">'+b.stages.map((s,i)=>'<div class="'+(s.id===active?'active':'')+'"><span>0'+(i+1)+'</span><b>'+esc(s.title)+'</b><small>'+esc(s.zh)+' · '+esc(s.en)+'</small></div>').join('<i>→</i>')+'</div>';
  }
  function shiftHtml(){
    const role=roleObject(session.role);
    return '<section class="fti-shell"><header class="fti-head compact"><div><span>FACTORY SHIFT · INTELLIGENCE</span><h1>'+esc(role?role.title:'')+' · '+(session.vehicle==='truck'?'Heavy Truck':'Passenger Vehicle')+'</h1></div><div class="fti-clock"><span id="ftiClock">12:00</span><button class="ghost" id="ftiExit">Выйти</button></div></header>'+mapHtml(session.events[0].stage)+'<div id="ftiKpis">'+kpiHtml()+'</div><div class="fti-event-grid"><div class="fti-event-card" id="ftiEvent"></div><aside class="fti-side"><div class="fti-chain" id="ftiChain"><b>Production Thread</b><span>Последствия ваших решений будут переходить в следующие цеха.</span></div><div class="fti-terms" id="ftiTerms"></div></aside></div></section>';
  }
  function dialogueHtml(e){
    const l=languageFor(session.index),voiceText=l==='english'?e.dialogue.en:e.dialogue.zh;
    return '<div class="fti-dialogue"><span>WORK DIALOGUE · '+(l==='english'?'ENGLISH':'普通话 · PUTONGHUA')+'</span>'+line(e.dialogue,session.index)+'<div class="fti-voice-row"><button id="ftiSpeak" '+(voiceAvailable()?'':'disabled')+'>Озвучить</button><button id="ftiSpeakSlow" class="ghost" '+(voiceAvailable()?'':'disabled')+'>Медленно</button><small>'+esc(voiceText)+'</small></div></div>';
  }
  function eventHtml(e){
    const stage=stageObject(e.stage),sev=e.severity==='red'?'RED':'YELLOW';
    return '<div class="fti-event-top"><div><span>Событие '+(session.index+1)+' / '+session.events.length+'</span><h2>'+esc(stage?stage.title:e.stage)+'</h2></div><strong data-severity="'+esc(e.severity)+'">ANDON · '+sev+'</strong></div>'+dialogueHtml(e)+'<div class="fti-problem">'+line(e,session.index)+'</div><div class="fti-question"><span>Решение для роли: '+esc((roleObject(session.role)||{}).title||'')+'</span><h3>Что вы делаете?</h3><div class="fti-actions">'+e.actions.map(a=>'<button data-fti-action="'+a+'">'+line(actionObject(a),session.index)+'</button>').join('')+'</div></div><div id="ftiOutcome" class="fti-outcome"></div>';
  }
  function termsHtml(stage){
    const list=VOCAB[stage]||[];return '<b>Лексика участка</b>'+list.map(t=>'<span><strong>'+esc(t[0])+'</strong><i>'+esc(t[1])+'</i><small>'+esc(t[2])+'</small></span>').join('');
  }
  function updateMap(stage){qa('.fti-map>div').forEach(x=>x.classList.toggle('active',q('b',x)&&q('b',x).textContent===(stageObject(stage)||{}).title))}
  function recalc(){
    const k=session.kpi;
    k.fpy=Math.max(0,Math.min(100,k.fpy));
    k.cycleSec=60+Math.min(90,k.downtime*3+session.mistakes*2+k.holds*2);
  }
  function actionImpact(action,correct,e){
    const k=session.kpi;
    if(correct){
      if(action==='rework'){k.rework+=1;k.downtime+=2;k.fpy-=2}
      else if(action==='hold'){k.holds+=1;k.downtime+=2;k.fpy-=1}
      else if(action==='stop'){k.downtime+=3;k.fpy-=1}
      else if(action==='call'||action==='quality'||action==='root'){k.downtime+=1}
      else if(action==='adjust'){k.downtime+=2}
      session.correct+=1;
    }else{
      session.mistakes+=1;k.fpy-=4;k.downtime+=2;
      session.stageMistakes[e.stage]=(session.stageMistakes[e.stage]||0)+1;
      (VOCAB[e.stage]||[]).forEach(t=>session.termMistakes[t[0]]=(session.termMistakes[t[0]]||0)+1);
      if(action==='continue'){
        if(e.severity==='red')session.severeEscapes+=1;
        session.latent.push({source:e.id,stage:e.stage,minStage:Math.min(5,stageIdx(e.stage)+1),applied:false,text:CONSEQUENCES[e.stage]});
      }
    }
    recalc();
  }
  function applyLatent(stage){
    const now=stageIdx(stage),applied=[];
    session.latent.forEach(c=>{
      if(!c.applied&&now>=c.minStage){
        c.applied=true;session.kpi.rework+=1;session.kpi.downtime+=4;session.kpi.holds+=1;session.kpi.fpy-=5;
        session.chain.push(c);applied.push(c);
      }
    });
    recalc();return applied;
  }
  function outcomeText(correct,chosen,e,applied){
    const expected=e.correct[session.role],action=actionObject(expected);
    let html='<div class="'+(correct?'ok':'bad')+'"><b>'+(correct?'Решение принято':'Решение создаёт риск')+'</b><span>'+(correct?'Действие соответствует роли и ситуации.':'Рекомендуемое действие: '+esc(action?action.ru:expected))+'</span></div>';
    if(!correct&&chosen==='continue')html+='<div class="carry"><b>Дефект пропущен дальше</b><span>Последствие проявится на следующем производственном этапе.</span></div>';
    if(applied&&applied.length)html+='<div class="carry"><b>Проявилось отложенное последствие</b><span>'+esc(applied.map(x=>x.text.ru).join(' '))+'</span></div>';
    return html;
  }
  function bindEvent(){
    q('#ftiSpeak').onclick=()=>speakCurrent(false);q('#ftiSpeakSlow').onclick=()=>speakCurrent(true);
    qa('[data-fti-action]').forEach(b=>b.onclick=()=>resolveAction(b.dataset.ftiAction));
  }
  function showEvent(){
    if(session.index>=session.events.length){finish();return}
    const e=session.events[session.index],applied=applyLatent(e.stage);
    q('#ftiEvent').innerHTML=eventHtml(e);q('#ftiTerms').innerHTML=termsHtml(e.stage);updateMap(e.stage);q('#ftiKpis').innerHTML=kpiHtml();
    if(applied.length)q('#ftiChain').innerHTML='<b>Production Thread · consequence</b><span>'+esc(applied.map(x=>x.text.ru).join(' '))+'</span>';
    bindEvent();if(session.autoVoice)setTimeout(()=>speakCurrent(false),180);
  }
  function resolveAction(chosen){
    if(session.locked)return;session.locked=true;
    const e=session.events[session.index],expected=e.correct[session.role],correct=chosen===expected;
    actionImpact(chosen,correct,e);
    session.history.push({event:e.id,stage:e.stage,chosen,expected,correct});
    const outcome=q('#ftiOutcome');outcome.innerHTML=outcomeText(correct,chosen,e,[]);
    qa('[data-fti-action]').forEach(b=>{b.disabled=true;b.classList.toggle('selected',b.dataset.ftiAction===chosen);b.classList.toggle('correct',b.dataset.ftiAction===expected)});
    q('#ftiKpis').innerHTML=kpiHtml();
    setTimeout(()=>{session.index+=1;session.locked=false;showEvent()},correct?900:1500);
  }
  function updateProfileAfterRun(){
    const p=profile();p.runs+=1;p.lastRole=session.role;
    STAGE_ORDER.forEach(id=>{p.stageMisses[id]=Math.max(0,(Number(p.stageMisses[id])||0)*.7+(session.stageMistakes[id]||0)*2)});
    Object.keys(session.termMistakes).forEach(t=>{p.termMisses[t]=Math.max(0,(Number(p.termMisses[t])||0)*.7+session.termMistakes[t])});
    saveProfile(p);return p;
  }
  function reportTerms(){
    const top=Object.keys(session.termMistakes).map(t=>({t,n:session.termMistakes[t]})).sort((a,b)=>b.n-a.n).slice(0,8);
    if(!top.length){
      const stages=topWeakStages(profile(),2);stages.forEach(s=>(VOCAB[s.id]||[]).slice(0,2).forEach(t=>top.push({t:t[0],n:1})));
    }
    return top;
  }
  function reportHtml(){
    const accuracy=session.history.length?Math.round(session.correct/session.history.length*100):0,p=updateProfileAfterRun(),weak=topWeakStages(p,3),terms=reportTerms(),cycle=Math.round(session.kpi.cycleSec),onTakt=cycle<=session.kpi.taktSec+5;
    return '<section class="fti-shell"><header class="fti-head"><div><span>SHIFT REPORT · FACTORY TRAINING INTELLIGENCE</span><h1>Отчёт смены</h1><p>Не игровые очки, а разбор производственных решений и тем для следующей тренировки.</p></div><button class="ghost" id="ftiReportClose">Игры</button></header>'+kpiHtml()+'<div class="fti-report-grid"><section><h2>Решения</h2><div class="fti-report-score"><b>'+accuracy+'%</b><span>точность решений</span></div><p>Правильно: '+session.correct+' / '+session.history.length+' · Ошибки: '+session.mistakes+' · Critical escapes: '+session.severeEscapes+'</p><p>Cycle '+cycle+' s при Takt '+session.kpi.taktSec+' s — <strong>'+(onTakt?'в пределах учебной цели':'выше учебной цели')+'</strong>.</p></section><section><h2>Следующая смена</h2><p>'+(weak.length?'Алгоритм усилит участки: <strong>'+weak.map(x=>esc((stageObject(x.id)||{}).title||x.id)).join(' · ')+'</strong>.':'Критических слабых участков пока нет — следующая смена останется сбалансированной.')+'</p><p>Выбор событий строится локально по истории ошибок этого браузера.</p></section><section><h2>Повторить лексику</h2><div class="fti-review-terms">'+(terms.length?terms.map(x=>'<span><b>'+esc(x.t)+'</b><small>'+esc(findTerm(x.t).slice(1).join(' · '))+'</small></span>').join(''):'<p>В этой смене нет выраженного словарного провала.</p>')+'</div></section><section><h2>Production Thread</h2><div class="fti-chain-report">'+(session.chain.length?session.chain.map(c=>'<p><b>'+esc((stageObject(c.stage)||{}).title||c.stage)+'</b><span>'+esc(c.text.ru)+'</span></p>').join(''):'<p>Ни один дефект не был ошибочно пропущен в следующий передел.</p>')+'</div></section></div><div class="fti-start"><button id="ftiAgain">Адаптивная следующая смена →</button><button id="ftiVocabulary" class="ghost">Показать KPI-словарь</button></div><div id="ftiKpiGlossary" class="fti-glossary"></div></section>';
  }
  function findTerm(term){for(const s of Object.keys(VOCAB)){for(const t of VOCAB[s])if(t[0]===term)return t}return[term,'','']}
  function glossaryHtml(){return Object.keys(KPI_TERMS).map(k=>{const x=KPI_TERMS[k];return '<div><b>'+esc(x.ru)+'</b><span>'+esc(x.zh)+' · '+esc(x.py)+'</span><small>'+esc(x.en)+'</small></div>'}).join('')}
  function finish(){clearInterval(timer);try{root.speechSynthesis&&root.speechSynthesis.cancel()}catch(_){}q('#main').innerHTML=reportHtml();q('#ftiReportClose').onclick=backToGames;q('#ftiAgain').onclick=open;q('#ftiVocabulary').onclick=()=>{q('#ftiKpiGlossary').innerHTML=glossaryHtml();q('#ftiVocabulary').disabled=true}}
  function startTimer(){clearInterval(timer);timer=setInterval(()=>{if(!session)return;session.seconds=Math.max(0,session.seconds-1);const m=String(Math.floor(session.seconds/60)).padStart(2,'0'),s=String(session.seconds%60).padStart(2,'0');const el=q('#ftiClock');if(el)el.textContent=m+':'+s;if(session.seconds===0)finish()},1000)}
  function backToGames(){clearInterval(timer);try{root.speechSynthesis&&root.speechSynthesis.cancel()}catch(_){}session=null;const nav=q('[data-view="games"]');if(nav)nav.click()}
  function open(){
    const b=base(),p=profile();if(!b)return;
    clearInterval(timer);session={role:p.lastRole||'operator',vehicle:'car',language:app().language==='english'?'english':'chinese',events:[],index:0,seconds:720,autoVoice:true,locked:false,correct:0,mistakes:0,severeEscapes:0,kpi:{fpy:100,rework:0,downtime:0,holds:0,taktSec:60,cycleSec:60},latent:[],chain:[],history:[],stageMistakes:{},termMistakes:{}};
    q('#main').innerHTML=setupHtml();q('#ftiClose').onclick=backToGames;
    qa('[data-fti-role]').forEach(but=>but.onclick=()=>{session.role=but.dataset.ftiRole;qa('[data-fti-role]').forEach(x=>x.classList.toggle('active',x===but))});
    qa('[data-fti-vehicle]').forEach(but=>but.onclick=()=>{session.vehicle=but.dataset.ftiVehicle;qa('[data-fti-vehicle]').forEach(x=>x.classList.toggle('active',x===but))});
    qa('[data-fti-lang]').forEach(but=>but.onclick=()=>{session.language=but.dataset.ftiLang;qa('[data-fti-lang]').forEach(x=>x.classList.toggle('active',x===but))});
    q('#ftiReset').onclick=()=>{resetProfile();q('.fti-profile span').textContent='Профиль сброшен. Следующая смена будет сбалансированной.'};
    q('#ftiStart').onclick=()=>{session.autoVoice=!!q('#ftiAutoVoice').checked;session.events=weightedEvents();q('#main').innerHTML=shiftHtml();q('#ftiExit').onclick=backToGames;showEvent();startTimer()};
  }
  function injectEntry(){
    if(app().view!=='games'||app().gameSession)return;const main=q('#main');if(!main||q('.factory-intelligence-entry',main))return;
    const anchor=q('.factory-stage2-entry',main)||q('.factory-process-entry',main);if(!anchor)return;
    const wrap=root.document.createElement('section');wrap.className='factory-intelligence-entry';wrap.innerHTML='<div class="section-title"><div><span class="kicker">FACTORY TRAINING INTELLIGENCE · v6.0.31</span><h2>Адаптивная производственная смена</h2><p>Последствия решений между цехами, FPY / Rework / Downtime / Takt, Shift Report и озвученные рабочие диалоги.</p></div></div><button class="fti-entry-card" id="ftiOpen"><span>~12 МИНУТ · ADAPTIVE</span><h3>Factory Shift Intelligence</h3><p>Operator / Engineer / Team Leader · 中文 + Pinyin / English / Mixed · локальный профиль ошибок</p><b>Начать интеллектуальную смену →</b></button>';anchor.parentNode.insertBefore(wrap,anchor.nextSibling);q('#ftiOpen',wrap).onclick=open;
  }
  function schedule(){if(pending)return;pending=true;root.requestAnimationFrame(()=>{pending=false;injectEntry()})}
  function install(){injectEntry();observer=new MutationObserver(schedule);observer.observe(root.document.body,{subtree:true,childList:true})}
  frontend.register('factory-training-intelligence-v631',{install,open,profile,resetProfile,kpis:KPI_TERMS});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
