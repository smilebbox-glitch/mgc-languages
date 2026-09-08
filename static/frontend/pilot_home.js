/* v6.0.17: company-pilot home dashboard for Chinese and English tracks. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('pilot-home')) return;

  let installed = false;
  let midnightTimer = null;

  const CHINESE_PHRASES = Object.freeze([
    ['生产线已经准备好了','Shēngchǎnxiàn yǐjīng zhǔnbèi hǎo le','Производственная линия уже готова.'],
    ['请确认零件是否到位','Qǐng quèrèn língjiàn shìfǒu dàowèi','Пожалуйста, подтвердите, что детали на месте.'],
    ['这个零件需要更换','Zhège língjiàn xūyào gēnghuàn','Эту деталь нужно заменить.'],
    ['请检查质量','Qǐng jiǎnchá zhìliàng','Пожалуйста, проверьте качество.'],
    ['设备已经启动','Shèbèi yǐjīng qǐdòng','Оборудование уже запущено.'],
    ['我们需要停止生产线','Wǒmen xūyào tíngzhǐ shēngchǎnxiàn','Нам нужно остановить производственную линию.'],
    ['请确认安全状态','Qǐng quèrèn ānquán zhuàngtài','Пожалуйста, подтвердите безопасное состояние.'],
    ['材料已经送到','Cáiliào yǐjīng sòng dào','Материалы уже доставлены.'],
    ['请按照作业指导书操作','Qǐng ànzhào zuòyè zhǐdǎoshū cāozuò','Работайте по рабочей инструкции.'],
    ['这个尺寸不符合要求','Zhège chǐcùn bù fúhé yāoqiú','Этот размер не соответствует требованиям.'],
    ['我们需要重新检查','Wǒmen xūyào chóngxīn jiǎnchá','Нам нужно проверить ещё раз.'],
    ['请记录这个问题','Qǐng jìlù zhège wèntí','Пожалуйста, зафиксируйте эту проблему.'],
    ['下一批什么时候到','Xià yī pī shénme shíhou dào','Когда прибудет следующая партия?'],
    ['请确认装配完成','Qǐng quèrèn zhuāngpèi wánchéng','Пожалуйста, подтвердите завершение сборки.'],
    ['这个问题已经解决','Zhège wèntí yǐjīng jiějué','Эта проблема уже решена.'],
    ['我们开始检查吧','Wǒmen kāishǐ jiǎnchá ba','Давайте начнём проверку.']
  ]);

  const ENGLISH_PHRASES = Object.freeze([
    ['The production line is ready.','Use this phrase before shift start or line handover.'],
    ['Please confirm the parts are in place.','Use it when checking material or component readiness.'],
    ['This part needs to be replaced.','A clear phrase for quality or assembly discussions.'],
    ['Please check the quality.','Use it when asking a colleague to verify the result.'],
    ['The equipment has started.','A simple status update for production teams.'],
    ['We need to stop the production line.','Use it when escalation or a controlled stop is required.'],
    ['Please confirm the safety status.','A concise phrase before work or restart.'],
    ['The materials have arrived.','Useful for logistics and production coordination.'],
    ['Please follow the work instruction.','Use it when referring to the approved standard process.'],
    ['This dimension is out of specification.','Useful in quality and engineering discussions.'],
    ['We need to check it again.','A neutral phrase for re-inspection.'],
    ['Please record this issue.','Use it when creating a traceable quality record.'],
    ['When will the next batch arrive?','Useful for logistics and planning.'],
    ['Please confirm assembly is complete.','Use it before handover to the next operation.'],
    ['This issue has been resolved.','A concise status update after corrective action.'],
    ["Let's start the inspection.",'Use it to begin a joint check with a colleague.']
  ]);

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function current() { return state().current(); }
  function esc(value) { return legacy().escapeHtml(value); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function nav() { return frontend.get('navigation'); }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(String(scope || 'pilot-home'), error && error.message ? error.message : error, '', 0, 0);
  }

  function owns(view) { return String(view || '') === 'home'; }

  function dayNumber(date) {
    const d = date || new Date();
    return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
  }

  function dailyPhrase(language, date) {
    const index = dayNumber(date);
    if (language === 'english') {
      const item = ENGLISH_PHRASES[((index % ENGLISH_PHRASES.length) + ENGLISH_PHRASES.length) % ENGLISH_PHRASES.length];
      return {term:item[0], pronunciation:'', translation:item[1], image:'/pilot/phrase-' + ((index % 7 + 7) % 7 + 1) + '.svg'};
    }
    const item = CHINESE_PHRASES[((index % CHINESE_PHRASES.length) + CHINESE_PHRASES.length) % CHINESE_PHRASES.length];
    return {term:item[0], pronunciation:item[1], translation:item[2], image:'/pilot/phrase-' + ((index % 7 + 7) % 7 + 1) + '.svg'};
  }

  function topicThumb(index) {
    return 'pilot-topic-' + ((Number(index || 0) % 6) + 1);
  }

  function safeNumber() {
    for (let i = 0; i < arguments.length; i += 1) {
      const value = Number(arguments[i]);
      if (Number.isFinite(value)) return value;
    }
    return 0;
  }

  function progressModel() {
    const snapshot = current();
    const summary = snapshot.summary || {};
    const progress = summary.progress || {};
    const game = snapshot.gamification || {};
    const totalTerms = safeNumber(progress.total_terms, summary.total_terms, 0);
    const knownTerms = safeNumber(progress.known_terms, progress.terms_known, summary.known_terms, 0);
    const learnedPercent = safeNumber(progress.percent, totalTerms ? Math.round(knownTerms * 100 / totalTerms) : 0);
    const days = safeNumber(progress.completed_days, 0);
    const bestExam = safeNumber(progress.best_exam, 0);
    return {
      knownTerms: knownTerms,
      totalTerms: totalTerms,
      learnedPercent: Math.max(0, Math.min(100, learnedPercent)),
      days: days,
      coursePercent: Math.max(0, Math.min(100, Math.round(days * 100 / 30))),
      examPercent: Math.max(0, Math.min(100, Math.round(bestExam * 100 / 50))),
      lifetimeXp: safeNumber(game.lifetime_xp, game.spendable_xp, 0),
      weeklyXp: safeNumber(game.weekly_xp, 0),
      spendableXp: safeNumber(game.spendable_xp, 0)
    };
  }

  function heroHTML(language) {
    const english = language === 'english';
    const heroClass = english ? 'pilot-hero pilot-hero-english' : 'pilot-hero pilot-hero-chinese';
    const title = english ? 'English for the automotive industry' : 'Китайский язык для автопрома';
    const subtitle = english ?
      'Learn professional terminology, real workplace situations, and effective communication for automotive teams.' :
      'Изучайте профессиональные термины, реальные рабочие ситуации и эффективную коммуникацию для команд в автомобильной отрасли.';
    const quote = english ? 'Language drives progress' : '让世界更好地出行';
    const quoteSmall = english ? 'Better communication for a better world.' : 'Лучшее движение для лучшего мира';
    return '<section class="' + heroClass + '"><div class="pilot-hero-copy"><div class="pilot-kicker">MGC LANGUAGE LAB</div>' +
      '<h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p><div class="pilot-hero-actions">' +
      '<button class="primary" data-pilot-target="topics">Выбрать тему <span>→</span></button>' +
      '<button class="pilot-soft-button" data-pilot-target="roleplay">▶ Начать сценарий</button></div></div>' +
      '<div class="pilot-hero-quote"><b>' + esc(quote) + '</b><span>' + esc(quoteSmall) + '</span></div>' +
      '<div class="pilot-hero-message">ЯЗЫК<br>ОБЪЕДИНЯЕТ<br>ЛЮДЕЙ<br>И ТЕХНОЛОГИИ</div></section>';
  }

  function todayPlanHTML() {
    return '<article class="pilot-panel pilot-today"><div class="pilot-panel-head"><span class="pilot-icon">▣</span><div><h3>План на сегодня</h3><small>3 коротких шага</small></div></div>' +
      '<button data-pilot-target="topics" class="pilot-task"><i></i><span><b>Изучить 8 терминов</b><small>Профессиональная лексика</small></span><em>›</em></button>' +
      '<button data-pilot-target="roleplay" class="pilot-task"><i></i><span><b>Пройти 1 сценарий</b><small>Реальная рабочая ситуация</small></span><em>›</em></button>' +
      '<button data-pilot-target="quiz" class="pilot-task"><i></i><span><b>Сделать мини-тест</b><small>Закрепить знания</small></span><em>›</em></button>' +
      '<button class="primary pilot-continue" data-pilot-target="topics">Продолжить обучение →</button></article>';
  }

  function phraseHTML(language) {
    const phrase = dailyPhrase(language);
    const chinese = language === 'chinese';
    return '<article class="pilot-panel pilot-phrase"><div class="pilot-panel-head"><span class="pilot-icon">❝</span><div><h3>Фраза дня</h3></div>' +
      '<button class="pilot-audio" data-speak-text="' + esc(phrase.term) + '" data-speak-language="' + esc(language) + '" aria-label="Послушать">🔊</button></div>' +
      '<div class="pilot-phrase-copy"><strong>' + esc(phrase.term) + '</strong>' +
      (chinese ? '<span class="pilot-pinyin">' + esc(phrase.pronunciation) + '</span>' : '') +
      '<p>' + esc(phrase.translation) + '</p></div><img class="pilot-phrase-image" src="' + esc(phrase.image) + '" alt="Автомобильное производство"></article>';
  }

  function quickHTML() {
    return '<article class="pilot-panel pilot-quick"><div class="pilot-panel-head"><span class="pilot-icon">ϟ</span><div><h3>Быстрый доступ</h3><small>Самые нужные инструменты</small></div></div>' +
      '<button class="pilot-quick-row" data-pilot-target="topics"><span class="pilot-qicon q-green">▤</span><div><b>Словарь</b><small>Термины и переводы</small></div><em>›</em></button>' +
      '<button class="pilot-quick-row" data-pilot-target="topics"><span class="pilot-qicon q-orange">≋</span><div><b>Произношение</b><small>Слушайте и повторяйте</small></div><em>›</em></button>' +
      '<button class="pilot-quick-row" data-pilot-target="course30"><span class="pilot-qicon q-violet">▰</span><div><b>Подборка терминов</b><small>Ключевые слова дня</small></div><em>›</em></button></article>';
  }

  function progressHTML() {
    const p = progressModel();
    const knownLabel = p.totalTerms ? (p.knownTerms + ' / ' + p.totalTerms) : (p.learnedPercent + '%');
    return '<section class="pilot-progress"><div class="pilot-section-head"><h2>Ваш прогресс</h2></div><div class="pilot-progress-grid">' +
      metric('▤','Изучено терминов',knownLabel,p.learnedPercent) + metric('▣','Дней в курсе',p.days + ' / 30',p.coursePercent) +
      metric('★','Результат экзамена',p.examPercent + '%',p.examPercent) + metric('✦','Всего XP',String(p.lifetimeXp),Math.min(100, Math.round((p.lifetimeXp % 1000) / 10))) +
      '</div></section>';
  }

  function metric(icon, label, value, percent) {
    return '<article class="pilot-metric"><span>' + icon + '</span><div><small>' + esc(label) + '</small><b>' + esc(value) + '</b><div class="pilot-meter"><i style="width:' + Number(percent || 0) + '%"></i></div><em>' + Number(percent || 0) + '%</em></div></article>';
  }

  function topicsHTML() {
    const topics = Array.isArray(current().topics) ? current().topics.slice(0, 6) : [];
    return '<section class="pilot-topics"><div class="pilot-section-head"><h2>Профессиональные темы</h2><button data-pilot-target="topics">Все темы →</button></div><div class="pilot-topic-grid">' +
      topics.map(function (topic, index) {
        return '<button class="pilot-topic" data-pilot-topic="' + esc(topic.label) + '"><span class="pilot-topic-thumb ' + topicThumb(index) + '"></span><b>' + esc(topic.label) + '</b><small>' + Number(topic.count || 0) + ' терминов</small><i></i></button>';
      }).join('') + '</div></section>';
  }

  function rightRailHTML() {
    const snapshot = current();
    const p = progressModel();
    const status = snapshot.pronunciationStatus || {};
    const nudge = (snapshot.nudges || [])[0];
    const audioLabel = status.server_available ? 'Серверное аудио доступно' : 'Доступен браузерный голос';
    return '<aside class="pilot-rail"><article class="pilot-rail-card"><div class="pilot-rail-title"><h3>Активность на этой неделе</h3></div>' +
      '<div class="pilot-week"><div><b>' + p.weeklyXp + '</b><span>XP за неделю</span></div><div><b>' + p.days + '</b><span>дней курса</span></div></div><p>Прогресс обновляется после учебных сессий.</p></article>' +
      '<article class="pilot-rail-card"><div class="pilot-rail-title"><h3>Произношение</h3></div><div class="pilot-pronounce"><span>◉</span><div><b>' + esc(audioLabel) + '</b><small>Аудио и повторение доступны в карточках терминов.</small></div></div><button data-pilot-target="topics">Открыть тренировку →</button></article>' +
      '<article class="pilot-rail-card"><div class="pilot-rail-title"><h3>Уведомления</h3><button data-pilot-target="notifications">Настроить</button></div>' +
      (nudge ? '<div class="pilot-nudge"><span>💡</span><div><b>' + esc(nudge.title) + '</b><small>' + esc(nudge.body) + '</small></div></div>' : '<p>Новых учебных напоминаний нет.</p>') + '</article>' +
      '<article class="pilot-quote-card"><b>Большие цели начинаются с маленьких слов.</b><span>— 每一步都很重要</span></article></aside>';
  }

  function syncChrome() {
    const snapshot = current();
    const user = snapshot.user || {};
    const name = query('#userProfileName');
    const dept = query('#userProfileDept');
    if (name) name.textContent = user.display_name || user.username || 'Пользователь';
    if (dept) dept.textContent = user.department || '';
    const search = query('#pilotSearch');
    if (search) search.placeholder = 'Поиск по темам…';
  }

  function render() {
    const snapshot = current();
    const main = query('#main');
    if (!main) throw new Error('Pilot home missing #main');
    state().set('view', 'home');
    syncChrome();
    main.innerHTML = '<div class="pilot-dashboard"><div class="pilot-primary">' + heroHTML(snapshot.language) +
      '<section class="pilot-next"><div class="pilot-next-head"><div><span class="pilot-icon">▣</span><div><h2>Ваш следующий шаг</h2><p>Небольшие шаги каждый день приводят к большим результатам.</p></div></div>' +
      '<blockquote>' + (snapshot.language === 'english' ? "Today's effort is tomorrow's success." : '今天的努力，是明天的成功。') + '</blockquote></div>' +
      '<div class="pilot-next-grid">' + todayPlanHTML() + phraseHTML(snapshot.language) + quickHTML() + '</div></section>' +
      progressHTML() + topicsHTML() + '</div>' + rightRailHTML() + '</div>';
    bindRenderedActions();
    scheduleMidnightRefresh();
  }

  function bindRenderedActions() {
    const main = query('#main');
    queryAll('[data-pilot-target]', main).forEach(function (button) {
      button.addEventListener('click', function () {
        nav().setView(button.dataset.pilotTarget).catch(function (error) { reportError('pilot-home-target', error); });
      });
    });
    queryAll('[data-pilot-topic]', main).forEach(function (button) {
      button.addEventListener('click', function () {
        state().patch({topic: button.dataset.pilotTopic, topicDetail: button.dataset.pilotTopic});
        nav().setView('topics').catch(function (error) { reportError('pilot-home-topic', error); });
      });
    });
  }

  function scheduleMidnightRefresh() {
    if (midnightTimer) root.clearTimeout(midnightTimer);
    const now = new Date();
    const next = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 2, 0);
    midnightTimer = root.setTimeout(function () {
      if (current().view === 'home') render();
    }, Math.max(1000, next.getTime() - now.getTime()));
  }

  function navigate(view) {
    if (!owns(view)) return nav().setView(view);
    legacy().closeMenu();
    queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === 'home');
    });
    try {
      render();
      return Promise.resolve();
    } catch (error) {
      reportError('pilot-home-navigation', error);
      return Promise.reject(error);
    }
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view="home"]') : null;
      if (!button) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate('home').catch(function () {});
    }, true);
    const search = query('#pilotSearch');
    if (search) {
      search.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter') return;
        const q = String(search.value || '').trim().toLowerCase();
        if (!q) return;
        const match = (current().topics || []).find(function (topic) {
          return String(topic.label || '').toLowerCase().includes(q);
        });
        if (!match) {
          legacy().toast('Тема не найдена. Попробуйте другое слово.');
          return;
        }
        state().patch({topic: match.label, topicDetail: match.label});
        nav().setView('topics').catch(function (error) { reportError('pilot-search', error); });
      });
    }
  }

  frontend.register('pilot-home', {
    views: Object.freeze(['home']),
    owns: owns,
    render: render,
    navigate: navigate,
    dailyPhrase: dailyPhrase,
    install: install
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
