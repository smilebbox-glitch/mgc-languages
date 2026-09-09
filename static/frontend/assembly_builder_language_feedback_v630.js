/* v6.0.30 — Assembly Builder learning-feedback localization.
 * Presentation-only patch: Russian UI, Chinese+pinyin or English learning feedback.
 */
(function(root){
  'use strict';
  const frontend=root.MGCFrontend;
  if(!frontend||frontend.has('assembly-builder-language-feedback-v630'))return;

  function q(sel,scope){return (scope||root.document).querySelector(sel)}
  function esc(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
  function module(){try{return frontend.get('assembly-builder-v630')}catch(_){return null}}
  function currentMode(mod){
    const title=q('.ab-head h1');if(!title||!mod)return null;
    return Object.keys(mod.modes||{}).find(function(key){return mod.modes[key].title===title.textContent.trim()})||null;
  }
  function taskIndex(){
    const p=q('#abProgress');if(!p)return 0;
    const m=String(p.textContent||'').match(/(\d+)\s*\/\s*10/);return m?Math.max(0,Math.min(9,Number(m[1])||0)):0;
  }
  function selectedLanguage(index){
    const active=q('[data-ab-lang].active');const value=active?active.dataset.abLang:'chinese';
    if(value==='mixed')return index%2===0?'chinese':'english';return value;
  }
  function patchSuccess(){
    const status=q('#abStatus');if(!status||status.textContent.indexOf('Верно.')!==0)return;
    const mod=module(),mode=currentMode(mod),index=taskIndex();if(!mod||!mode)return;
    const task=mod.tasks&&mod.tasks[mode]&&mod.tasks[mode][index];if(!task)return;
    const lang=selectedLanguage(index);
    status.innerHTML=lang==='english'
      ? '<b>Верно.</b> '+esc(task.phraseEn)+'<small>'+esc(task.phraseRu)+'</small>'
      : '<b>Верно.</b> '+esc(task.phraseZh)+' <em>'+esc(task.phrasePy)+'</em><small>'+esc(task.phraseRu)+'</small>';
  }
  function install(){
    root.document.addEventListener('click',function(event){
      if(!event.target.closest||!event.target.closest('.ab3d-marker'))return;
      root.setTimeout(patchSuccess,0);
    });
  }
  frontend.register('assembly-builder-language-feedback-v630',{install:install});
  if(root.document.readyState==='loading')root.document.addEventListener('DOMContentLoaded',install,{once:true});else install();
})(window);
