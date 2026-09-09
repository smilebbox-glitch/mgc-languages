/* v6.0.30 — Chinese learning-surface consistency.
 * Presentation only. Canonical answers, XP, scoring and API semantics remain unchanged.
 */
(function (root) {
  'use strict';

  const main = root.document.getElementById('main');
  if (!main) return;

  const EXACT = Object.freeze({
    // Quiz
    'Проверка знаний':'知识检查',
    'Тест по теме':'主题测试',
    'До 10 вопросов. Pinyin можно включать и выключать; произношение доступно отдельной кнопкой.':'最多 10 道题。可开启或关闭拼音，并可单独播放发音。',
    'Тема':'主题',
    'Уровень':'级别',
    'Начать тест':'开始测试',
    'Тест завершён':'测试完成',
    'Результат':'结果',
    'Вы можете повторить тему или перейти к рабочим сценариям.':'您可以复习该主题或进入工作场景训练。',
    'Правильных ответов':'正确答案',
    'Пройти ещё раз':'再做一次',
    'Сценарии по теме':'主题场景',
    'Подсказка · 10 XP':'提示 · 10 XP',
    'Убрать вариант · 20 XP':'排除一个选项 · 20 XP',
    'Показать результат':'查看结果',
    'Следующий вопрос':'下一题',
    'Верно':'正确',

    // Role play
    'Практика':'练习',
    'Сценарии':'场景',
    'Для выбранной темы сценариев пока нет.':'当前主题暂无场景。',
    'Выбрать другую тему':'选择其他主题',
    'Коммуникационный тренажёр':'沟通训练',
    'Рабочие сценарии':'工作场景',
    'Ситуации, MGC-сценарии и Role Play объединены в одну мини-игру.':'实际情况、MGC 场景与角色扮演整合为一个训练模块。',
    'Все':'全部',
    'Вопрос':'问题',
    'Начать круг заново':'重新开始',
    'Следующая ситуация':'下一个场景',
    'Посмотрите профессиональную формулировку':'请查看专业表达',
    'Цель:':'目标：',

    // 30-day course
    'Учебная программа':'学习计划',
    '30 дней':'30 天',
    'Программа пока недоступна.':'学习计划暂不可用。',
    'Каждый день: новые термины, короткая активность, рабочий кейс и обязательный тест.':'每天：新术语、短练习、工作案例和必做测试。',
    'завершено':'已完成',
    'Термины дня':'今日术语',
    'Активность':'练习',
    'Соберите пару':'配对练习',
    'Выберите перевод для термина.':'请选择术语对应的含义。',
    'Мини-кейс по теме':'主题小案例',
    'Пройти тест дня · 5 вопросов':'完成今日测试 · 5 题',
    'Тест дня завершён':'今日测试完成',
    'Нужно ещё одно повторение':'需要再复习一次',
    'Результат сохранён в вашем прогрессе.':'结果已保存到您的学习进度。',
    'Для зачёта нужно минимум 4 правильных ответа из 5.':'通过需要至少答对 5 题中的 4 题。',
    'Отлично — следующий день открыт.':'很好，下一天已解锁。',
    'Повторите термины и попробуйте снова.':'请复习术语后再试一次。',
    'Вернуться к курсу':'返回课程',
    'Повторить материал':'复习内容',
    '← К материалу дня':'← 返回今日内容',
    'Завершить тест':'完成测试',
    'Следующий термин':'下一个术语',
    'Пара показана выше':'正确配对已显示',
    'Разбор терминов':'术语学习',
    'Собрать пары':'配对',
    'Мини-кейс':'小案例',
    'Тест из 5 вопросов':'5 题测试',

    // XP
    'XP economy':'XP 学习积分',
    'Опыт, который помогает учиться':'帮助学习的 XP',
    'Уровень не уменьшается. Тратится только доступный баланс XP; основные рабочие функции сервиса всегда бесплатны.':'等级不会下降，只会使用可用 XP 余额；平台的核心学习功能始终可用。',
    'Практическая помощь':'学习辅助',
    'Активировать':'启用',
    'Используется прямо внутри задания':'直接在任务中使用',
    'Использовать XP →':'使用 XP →',
    'Открытая практика':'开放练习',
    'Персональная тренировка':'个性化训练',
    'Lifetime:':'累计：',
    'доступно для помощи:':'可用于辅助：',
    'неделя:':'本周：',

    // Arcade mastery / game profile
    'ARCADE MASTERY · SKILL MAP':'游戏能力 · 技能图谱',
    'Карта навыков по вашей игровой практике':'根据游戏练习生成的技能图谱',
    'Сервис переводит результаты 20 игр в семь рабочих компетенций и показывает, что тренировать дальше.':'系统把 20 个游戏的结果汇总为 7 项工作能力，并提示下一步训练方向。',
    'ПРИОРИТЕТ ЦЕХА':'车间重点',
    'НАВЫК':'技能',
    'СЛЕДУЮЩИЙ АПГРЕЙД':'下一步提升',
    'Тренировать слабое место →':'训练薄弱项 →',
    'Достижения':'成就',
    'Без искусственного фарма XP':'不通过重复刷取 XP',
    'фокус вашего отдела':'部门重点',
    'механик попробовано':'已尝试游戏',
    'идеальных 5/5':'满分 5/5',
    'активных дней':'活跃天数',
    'Нет доступной игры':'暂无可用游戏',
    'Практика':'练习',
    'Терминология':'术语',
    'Аудирование':'听力',
    'Производство':'生产',
    'Качество':'质量',
    'Логистика':'物流',
    'Инженерия':'工程',
    'Коммуникация':'沟通',
    'Первый заезд':'首次训练',
    'Попробовать 3 механики':'尝试 3 种游戏',
    'Исследователь':'探索者',
    'Попробовать 10 механик':'尝试 10 种游戏',
    'Полный гараж':'完整车库',
    'Попробовать все 20 механик':'尝试全部 20 种游戏',
    'Чистая смена':'完美班次',
    'Получить пять результатов 5/5':'获得 5 次满分 5/5',
    'Стабильность':'稳定学习',
    'Пять активных дней':'连续 5 个活跃日',
    'Цеховой специалист':'车间专家',
    '70% по приоритетным навыкам':'重点技能达到 70%',
    'MASTER':'大师',
    'EXPERT':'专家',
    'SPECIALIST':'专业级',
    'OPERATOR':'熟练级',
    'DEVELOPING':'提升中',
    'ROOKIE':'入门级',

    // Common automotive topics shown by course/scenarios
    'Сварка кузова':'车身焊装',
    'Окраска':'涂装',
    'Штамповка':'冲压',
    '3D-печать':'3D 打印',
    'Литьё пластмасс':'注塑',
    'Оснастка и пресс-формы':'工装与模具',
    'Сиденья и интерьер':'座椅与内饰',
    'Пассивная безопасность':'被动安全',
    'Двигатель и трансмиссия':'动力总成',
    'Электрика, ПО и ADAS':'电气、软件与 ADAS',
    'IT, AI и автоматизация':'IT、AI 与自动化',
    'Гарантия и сервис':'质保与售后',
    'Качество и APQP':'质量与 APQP',
    'R&D и инженерия':'研发与工程',
    'Проекты и запуск':'项目与投产',
    'Закупки и поставщики':'采购与供应商',
    'Логистика JIT/JIS':'物流 JIT/JIS',
    'Безопасность и омологация':'安全与认证',
    'Переговоры и культура':'商务沟通与文化',
    'Финансы и JV':'财务与合资',
    'Производство и сборка':'生产与总装'
  });

  const PARTIAL = Object.freeze([
    ['Следующее: ','下一项：'],
    ['Баланс: ','余额：'],
    ['УРОВЕНЬ ','等级 '],
    ['День ','第 '],
    [' · вопрос ',' · 第 '],
    [' из 5',' / 5'],
    [' сценариев попробовано',' 个场景已尝试'],
    ['Правильный ответ: ','正确答案：'],
    ['Лучший тест: ','最佳测试：'],
    ['Зачёт: ','通过：'],
    [' дней',' 天']
  ]);

  const originals = new WeakMap();
  let queued = false;

  function snapshot() {
    try {
      const frontend = root.MGCFrontend;
      return frontend && frontend.has && frontend.has('app-state') ? frontend.get('app-state').current() : {};
    } catch (_) { return {}; }
  }
  function chinese() { return snapshot().language === 'chinese'; }
  function relevantView() {
    return ['games','xp','quiz','roleplay','course30'].includes(String(snapshot().view || ''));
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
  function localizeText() {
    if (!relevantView()) return;
    const walker = root.document.createTreeWalker(main, root.NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (node) {
      const parent = node.parentElement;
      if (!parent || parent.closest('script,style,.pinyin,.pinyin-line,.question-pinyin,.ipa-line,.reading-line')) return;
      if (!originals.has(node)) originals.set(node, node.nodeValue || '');
      const original = originals.get(node);
      const target = chinese() ? translated(original) : original;
      if (node.nodeValue !== target) node.nodeValue = target;
    });
  }
  function optionPinyin(question, selector) {
    main.querySelectorAll(selector).forEach(function (button, index) {
      let node = button.querySelector('.v630-option-pinyin');
      const value = chinese() && question && Array.isArray(question.option_pronunciations)
        ? String(question.option_pronunciations[index] || '') : '';
      if (!value) {
        if (node) node.remove();
        return;
      }
      if (!node) {
        node = root.document.createElement('span');
        node.className = 'pinyin-line v630-option-pinyin';
        button.appendChild(node);
      }
      node.textContent = value;
    });
  }
  function injectQuizPinyin() {
    const state = snapshot();
    if (String(state.view || '') === 'quiz' && Array.isArray(state.quiz)) {
      optionPinyin(state.quiz[state.quizIndex], '[data-answer]');
    }
    if (String(state.view || '') === 'course30' && Array.isArray(state.dayQuiz)) {
      optionPinyin(state.dayQuiz[state.dayQuizIndex], '[data-day-answer]');
    }
  }
  function mark() {
    main.classList.toggle('v630-chinese-learning-surface', chinese() && relevantView());
  }
  function apply() {
    mark();
    localizeText();
    injectQuizPinyin();
  }
  function schedule() {
    if (queued) return;
    queued = true;
    root.requestAnimationFrame(function () {
      queued = false;
      apply();
    });
  }

  new MutationObserver(schedule).observe(main, {childList:true, subtree:true, characterData:true});
  root.document.addEventListener('mgc:state-change', schedule);
  root.document.addEventListener('click', function (event) {
    if (!event.target || !event.target.closest) return;
    if (event.target.closest('[data-language],[data-view],[data-go],[data-answer],[data-day-answer],[data-scenario-answer]')) {
      root.setTimeout(schedule, 0);
      root.setTimeout(schedule, 80);
    }
  }, true);
  schedule();
})(window);
