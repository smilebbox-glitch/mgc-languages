/* v6.0.30 — Chinese Automotive Arcade localization layer.
 * Presentation only: never changes canonical answer values, scoring, XP or API calls.
 */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const GAME_TITLES = Object.freeze({
    match:{zh:'词语配对',py:'cíyǔ pèiduì'},
    listening:{zh:'听力冲刺',py:'tīnglì chōngcì'},
    mistake:{zh:'精准检查',py:'jīngzhǔn jiǎnchá'},
    phrase:{zh:'句子构建',py:'jùzi gòujiàn'},
    hotspot:{zh:'汽车部件定位',py:'qìchē bùjiàn dìngwèi'},
    assembly_order:{zh:'汽车装配',py:'qìchē zhuāngpèi'},
    shop_route:{zh:'工厂路线',py:'gōngchǎng lùxiàn'},
    tool_select:{zh:'工具选择',py:'gōngjù xuǎnzé'},
    defect_detective:{zh:'缺陷识别',py:'quēxiàn shíbié'},
    safety_spot:{zh:'安全隐患识别',py:'ānquán yǐnhuàn shíbié'},
    quality_gate:{zh:'质量关',py:'zhìliàng guān'},
    logistics_route:{zh:'物流流程',py:'wùliú liúchéng'},
    kanban:{zh:'看板挑战',py:'kànbǎn tiǎozhàn'},
    bom_builder:{zh:'物料清单构建',py:'wùliào qīngdān gòujiàn'},
    spec_check:{zh:'规格判定',py:'guīgé pàndìng'},
    rapid_recall:{zh:'十秒回忆',py:'shí miǎo huíyì'},
    memory_pairs:{zh:'记忆车库',py:'jìyì chēkù'},
    odd_one_out:{zh:'找出异类',py:'zhǎochū yìlèi'},
    dialogue_choice:{zh:'对话挑战',py:'duìhuà tiǎozhàn'},
    shift_incident:{zh:'班次事件',py:'bāncì shìjiàn'}
  });

  const EXACT = Object.freeze({
    'Word Match':'词语配对',
    'Listening Sprint':'听力冲刺',
    'Precision Check':'精准检查',
    'Phrase Builder':'句子构建',
    'Car Part Hotspot':'汽车部件定位',
    'Build the Car':'汽车装配',
    'Factory Router':'工厂路线',
    'Tool Selector':'工具选择',
    'Defect Detective':'缺陷识别',
    'Safety Spot':'安全隐患识别',
    'Quality Gate':'质量关',
    'Logistics Flow':'物流流程',
    'Kanban Challenge':'看板挑战',
    'Build the BOM':'物料清单构建',
    'Spec or NOK?':'规格判定',
    '10-Second Recall':'十秒回忆',
    'Memory Garage':'记忆车库',
    'Odd One Out':'找出异类',
    'Dialogue Duel':'对话挑战',
    'Shift Incident':'班次事件',

    'PASS':'合格',
    'REWORK':'返工',
    'HOLD':'暂停',

    'ASN':'预到货通知',
    'Receiving':'收货',
    'Scan':'扫码',
    'Put-away':'入库',
    'Line replenishment':'线边补货',
    'Pick':'拣选',
    'Pack':'包装',
    'Label':'贴标',
    'Load':'装车',
    'Ship':'发运',
    'Booking':'订舱',
    'Pickup':'提货',
    'Customs':'海关',
    'Transport':'运输',
    'Delivery':'交付',
    'Count':'盘点',
    'Reconcile':'核对',
    'Correct':'纠正',
    'Release':'放行',
    'Report':'报告',
    'Shortage signal':'缺料信号',
    'Confirm stock':'确认库存',
    'Expedite':'加急',
    'Deliver':'配送',
    'Close alert':'关闭预警',

    'bumper':'保险杠',
    'door':'车门',
    'fender':'翼子板',
    'hood':'发动机罩',
    'seat':'座椅',
    'instrument panel':'仪表板',
    'headliner':'顶棚',
    'carpet':'地毯',
    'ECU':'电子控制单元',
    'sensor':'传感器',
    'wiring harness':'线束',
    'relay':'继电器',
    'brake disc':'制动盘',
    'subframe':'副车架',
    'steering rack':'转向齿条',
    'damper':'减振器',
    'pallet':'托盘',
    'returnable container':'可循环容器',
    'label':'标签',
    'barcode':'条码',

    'Gap':'间隙',
    'Flush':'面差',
    'Torque':'扭矩',
    'Film thickness':'漆膜厚度',
    'Pressure':'压力',

    'Visual inspection':'外观检查',
    'MACHINE':'设备',
    'SPEC':'规格',
    'VEHICLE':'整车',
    'BODY':'车身',
    'MODULE':'模块',
    'COMPONENT':'部件',
    'SHIFT INCIDENT':'班次事件',
    'DIALOGUE DUEL':'对话挑战',
    'LIVE':'进行中',
    'SEC':'秒',
    'max 5':'最多 5 题',

    'ASSEMBLY LINE · LIVE':'总装线 · 运行中',
    'Body':'车身',
    'Trim':'内饰',
    'Chassis':'底盘',
    'Final':'终检',
    'LINE RUNNING':'生产线运行中',
    'BODY SHOP · ROBOT CELL':'焊装车间 · 机器人单元',
    'CELL SAFE':'单元安全',
    'BIW / spot welding':'白车身 / 点焊',
    'PAINT SHOP · INSPECTION':'涂装车间 · 检查',
    'scratch':'划痕',
    'paint run':'流挂',
    'orange peel':'橘皮',
    'INSPECTION ACTIVE':'检查进行中',
    'surface quality':'表面质量',
    'INTRALOGISTICS · MATERIAL FLOW':'厂内物流 · 物料流',
    'Dock':'卸货区',
    'Supermarket':'物料超市',
    'Line side':'线边',
    'FLOW SYNCHRONIZED':'物流同步',
    'FIFO · Kanban':'FIFO · 看板',

    'QUALITY GATE':'质量关',
    'SPEC CHECK':'规格检查',
    'PRECISION':'精准检查',
    'NOMINAL':'名义值',
    'MEASUREMENT LIVE':'测量进行中',
    'CMM · tolerance · disposition':'三坐标测量 · 公差 · 处置',
    'BOM DIGITAL THREAD':'物料清单数字线程',
    'ENGINEERING CLASSIFICATION':'工程分类',
    'ENGINEERING':'工程',
    'A3 DRAWING':'A3 图纸',
    'REV':'版本',
    'released':'已发布',
    'DIGITAL THREAD LINKED':'数字线程已连接',
    'drawing · BOM · subsystem':'图纸 · 物料清单 · 子系统',

    'MISSION FLOW':'任务进度',
    'MISSION BRIEFING':'任务简报',
    'MISSION COMPLETE':'任务完成',
    'GAME WORLD':'游戏世界',
    'Factory Hub':'工厂中心',
    'Automotive Arcade':'汽车工厂游戏',
    'Garage':'车库'
  });

  const PARTIAL = Object.freeze([
    ['MGC AUTOMOTIVE ARCADE · 20 ИГР','MGC 汽车游戏中心 · 20 个游戏'],
    ['PASS / REWORK / HOLD','合格 / 返工 / 暂停'],
    ['Dock → Supermarket → Line side','卸货区 → 物料超市 → 线边'],
    ['Vehicle → System → Component','整车 → 系统 → 部件'],
    ['QUALITY LAB · QUALITY GATE','质量实验室 · 质量关'],
    ['QUALITY LAB · SPEC CHECK','质量实验室 · 规格检查'],
    ['QUALITY LAB · PRECISION','质量实验室 · 精准检查'],
    ['ENGINEERING · ENGINEERING CLASSIFICATION','工程 · 工程分类'],
    ['ENGINEERING · BOM DIGITAL THREAD','工程 · 物料清单数字线程'],
    ['BOM DIGITAL THREAD','物料清单数字线程'],
    ['BOM / subsystem','物料清单 / 子系统'],
    ['takt 60 s','节拍 60 秒'],
    ['Near miss','险情'],
    ['Gap:','间隙：'],
    ['Flush:','面差：'],
    ['Torque:','扭矩：'],
    ['Film thickness:','漆膜厚度：'],
    ['Pressure:','压力：'],
    ['BODY','车身'],
    ['MODULE','模块'],
    ['COMPONENT','部件'],
    ['Kanban','看板'],
    ['BOM','物料清单']
  ]);

  const originals = new WeakMap();
  let queued = false;

  function frontend() { return root.MGCFrontend || null; }
  function snapshot() {
    try {
      const f = frontend();
      return f && f.has && f.has('app-state') ? f.get('app-state').current() : {};
    } catch (_) { return {}; }
  }
  function isChinese() { return snapshot().language === 'chinese'; }
  function activeGameType() {
    const state = snapshot();
    const session = state.gameSessionV618 || state.gameSession || null;
    return session && session.game_type ? String(session.game_type) : '';
  }

  function translated(value) {
    const raw = String(value == null ? '' : value);
    const leading = raw.match(/^\s*/)[0];
    const trailing = raw.match(/\s*$/)[0];
    const core = raw.trim();
    if (!core) return raw;
    if (Object.prototype.hasOwnProperty.call(EXACT, core)) return leading + EXACT[core] + trailing;
    let next = core;
    PARTIAL.forEach(function (pair) { next = next.split(pair[0]).join(pair[1]); });
    return leading + next + trailing;
  }

  function localizeTextNodes() {
    const walker = root.document.createTreeWalker(main, root.NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (node) {
      const parent = node.parentElement;
      if (!parent || parent.closest('script,style')) return;
      if (!originals.has(node)) originals.set(node, node.nodeValue || '');
      const original = originals.get(node);
      const target = isChinese() ? translated(original) : original;
      if (node.nodeValue !== target) node.nodeValue = target;
    });
  }

  function addPinyinLabel(container, gameType) {
    if (!container || !gameType || !GAME_TITLES[gameType]) return;
    const title = GAME_TITLES[gameType];
    let pinyin = container.querySelector(':scope > .gw30-zh-title-pinyin');
    if (!isChinese()) {
      if (pinyin) pinyin.remove();
      return;
    }
    if (!pinyin) {
      pinyin = root.document.createElement('span');
      pinyin.className = 'question-pinyin gw30-zh-title-pinyin';
      container.appendChild(pinyin);
    }
    if (pinyin.textContent !== title.py) pinyin.textContent = title.py;
  }

  function localizeCatalogTitles() {
    main.querySelectorAll('[data-start-v618-game],[data-start-game]').forEach(function (card) {
      const type = String(card.dataset.startV618Game || card.dataset.startGame || '');
      const title = card.querySelector('h3');
      if (!title || !GAME_TITLES[type]) return;
      if (!title.dataset.gw30ZhOriginal) title.dataset.gw30ZhOriginal = title.textContent || '';
      const target = isChinese() ? GAME_TITLES[type].zh : title.dataset.gw30ZhOriginal;
      if (title.textContent !== target) title.textContent = target;
      const copy = card.querySelector('.game-lab-copy') || title.parentElement;
      addPinyinLabel(copy, type);
    });
  }

  function localizeActiveTitle() {
    const type = activeGameType();
    const title = main.querySelector('.page-head h1');
    if (!title || !type || !GAME_TITLES[type]) return;
    if (!title.dataset.gw30ZhOriginal) title.dataset.gw30ZhOriginal = title.textContent || '';
    const target = isChinese() ? GAME_TITLES[type].zh : title.dataset.gw30ZhOriginal;
    if (title.textContent !== target) title.textContent = target;
    addPinyinLabel(title.parentElement, type);
  }

  function markLanguage() {
    main.classList.toggle('gw30-chinese-games', isChinese());
    main.setAttribute('data-game-language-surface', isChinese() ? 'chinese' : 'english');
  }

  function localize() {
    markLanguage();
    localizeTextNodes();
    localizeCatalogTitles();
    localizeActiveTitle();
  }

  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () {
      queued = false;
      localize();
    });
  }

  new MutationObserver(schedule).observe(main,{childList:true,subtree:true,characterData:true});
  root.document.addEventListener('click',function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-language],[data-view="games"],[data-start-v618-game],[data-start-game],[data-replay-v618],[data-go-games-home]')) {
      root.setTimeout(schedule,0);
      root.setTimeout(schedule,120);
    }
  },true);
  root.addEventListener('popstate',schedule);
  schedule();
})(window);
