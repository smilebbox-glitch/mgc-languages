/* v6.0.30 Stage D — presentation-only localization for process motion labels. */
(function (root) {
  'use strict';
  const main = root.document.getElementById('main');
  if (!main) return;

  const ZH = Object.freeze({
    'PROCESS LIVE':'生产过程 · 运行中',
    'LINE SIGNAL':'生产线信号','OPERATOR CALL':'操作员指令','PRECISION CHECK':'精准检查',
    'WORK INSTRUCTION':'作业指导','PART INSTALL':'部件安装','STATION SEQUENCE':'工位顺序',
    'PLANT ROUTE':'工厂路线','TORQUE VERIFY':'扭矩确认','SURFACE SCAN':'表面扫描',
    'SAFETY INTERLOCK':'安全联锁','QUALITY DISPOSITION':'质量处置','AGV ROUTE':'AGV 路线',
    'KANBAN REPLENISH':'看板补料','BOM DIGITAL THREAD':'物料清单数字线程','CMM PROBE':'三坐标测头',
    'TAKT RESPONSE':'节拍响应','PART KITTING':'零件配套','SYSTEM CLASSIFICATION':'系统分类',
    'CONTROL ROOM':'控制室','CONTAINMENT':'遏制',
    'PART':'部件','FIT':'安装','VERIFY':'确认','RELEASE':'放行',
    'CLAMP':'夹紧','WELD':'焊接','CHECK':'检查','SPRAY':'喷涂','FLASH':'闪干','SCAN':'扫描','OK':'合格',
    'CALL':'呼叫','PICK':'拣选','MOVE':'搬运','DELIVER':'配送','LOCATE':'定位','PROBE':'测量','COMPARE':'比较','STATUS':'状态',
    'DRAWING':'图纸','LINK':'连接','BOM':'物料清单','NOTICE':'发现','DECIDE':'决策','CONFIRM':'确认',
    'DOCK':'卸货区','MARKET':'物料超市','LINE':'线边','ACTUAL':'实测值','VEHICLE':'整车','SYSTEM':'系统','MODULE':'模块',
    'RELEASED':'已发布','LINE 01':'生产线 01','TAKT s':'节拍 秒'
  });

  const originals = new WeakMap();
  let queued = false;

  function snapshot() {
    try {
      const f = root.MGCFrontend;
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }
  function isChinese() { return snapshot().language === 'chinese'; }
  function localize() {
    main.querySelectorAll('.gw30d-rig *').forEach(function (node) {
      if (node.children.length) return;
      if (!originals.has(node)) originals.set(node,node.textContent || '');
      const original = originals.get(node);
      const core = original.trim();
      const target = isChinese() && ZH[core] ? original.replace(core,ZH[core]) : original;
      if (node.textContent !== target) node.textContent = target;
    });
  }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () { queued = false; localize(); });
  }

  new MutationObserver(schedule).observe(main,{childList:true,subtree:true,characterData:true});
  root.document.addEventListener('click',function (event) {
    if (event.target && event.target.closest && event.target.closest('[data-language],[data-view="games"],[data-start-v618-game],[data-start-game]')) {
      root.setTimeout(schedule,0);
      root.setTimeout(schedule,100);
    }
  },true);
  schedule();
})(window);
