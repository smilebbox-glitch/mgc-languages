/* v6.0.31 premium-home refresh: editorial automotive learning workspace. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('premium-home')) return;

  function state() { return frontend.get('app-state'); }
  function current() { return state().current(); }
  function nav() { return frontend.get('navigation'); }
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char];
    });
  }
  function safeNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : Number(fallback || 0);
  }
  function owns(view) { return String(view || '') === 'home'; }

  const CHINESE_MISSIONS = Object.freeze([
    {
      cn: '我们需要确认交付日期。',
      pinyin: 'Wǒmen xūyào quèrèn jiāofù rìqī.',
      ru: 'Нам нужно подтвердить дату поставки.',
      title: 'Поставщик задержал партию компонентов',
      goal: 'Уточнить причину задержки, согласовать новый срок и зафиксировать ответственность сторон.',
      terms: [['交付日期','дата поставки'],['延期','задержка / перенос'],['确认','подтвердить']]
    },
    {
      cn: '这个尺寸不符合图纸要求。',
      pinyin: 'Zhège chǐcùn bù fúhé túzhǐ yāoqiú.',
      ru: 'Этот размер не соответствует требованиям чертежа.',
      title: 'На линии обнаружено отклонение по размеру',
      goal: 'Корректно описать несоответствие, запросить проверку и согласовать следующее действие.',
      terms: [['尺寸','размер'],['图纸','чертёж'],['不符合','не соответствует']]
    },
    {
      cn: '请确认装配完成。',
      pinyin: 'Qǐng quèrèn zhuāngpèi wánchéng.',
      ru: 'Пожалуйста, подтвердите завершение сборки.',
      title: 'Передача автомобиля на следующую операцию',
      goal: 'Подтвердить завершение сборки и передать статус следующему участку без двусмысленности.',
      terms: [['装配','сборка'],['完成','завершить'],['确认','подтвердить']]
    }
  ]);

  const ENGLISH_MISSIONS = Object.freeze([
    {
      en: 'We need to confirm the delivery date.',
      ru: 'Нам нужно подтвердить дату поставки.',
      title: 'Supplier delivery is delayed',
      goal: 'Clarify the cause, agree a revised delivery date and confirm ownership of the next action.',
      terms: [['delivery date','дата поставки'],['delay','задержка'],['confirm','подтвердить']]
    },
    {
      en: 'This dimension is out of specification.',
      ru: 'Этот размер вне допуска.',
      title: 'A dimensional deviation was found on the line',
      goal: 'Describe the deviation precisely, request verification and agree the containment action.',
      terms: [['dimension','размер'],['specification','требование / допуск'],['verify','проверить']]
    },
    {
      en: 'Please confirm assembly is complete.',
      ru: 'Пожалуйста, подтвердите завершение сборки.',
      title: 'Vehicle handover to the next operation',
      goal: 'Confirm completion and communicate the status to the next production area.',
      terms: [['assembly','сборка'],['complete','завершено'],['handover','передача']]
    }
  ]);

  function dayIndex() {
    const now = new Date();
    return Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000);
  }

  function mission(language) {
    const list = language === 'english' ? ENGLISH_MISSIONS : CHINESE_MISSIONS;
    return list[((dayIndex() % list.length) + list.length) % list.length];
  }

  function progress() {
    const snap = current();
    const summary = snap.summary || {};
    const p = summary.progress || {};
    const days = Math.max(0, Math.min(30, safeNumber(p.completed_days, 0)));
    return { day: Math.max(1, Math.min(30, days + 1)) };
  }

  function userName() {
    const user = current().user || {};
    return user.display_name || user.name || user.username || 'Пользователь';
  }

  function headerHTML(language) {
    return '<header class="v631p-header">' +
      '<button class="v631p-brand" data-v631-target="home" aria-label="Главная"><b>MGC</b><span>LANGUAGE LAB</span></button>' +
      '<nav class="v631p-nav" aria-label="Разделы обучения">' +
      '<button class="active" data-v631-target="home">Главная</button>' +
      '<button data-v631-target="topics">Темы</button>' +
      '<button data-v631-target="roleplay">Сценарии</button>' +
      '<button data-v631-target="course30">30 дней</button>' +
      '<button data-v631-target="games">Игры</button>' +
      '<button data-v631-target="exam">Экзамен</button></nav>' +
      '<div class="v631p-header-right"><div class="v631p-language" role="group" aria-label="Изучаемый язык">' +
      '<button data-v631-language="chinese" class="' + (language === 'chinese' ? 'active' : '') + '">中文</button>' +
      '<button data-v631-language="english" class="' + (language === 'english' ? 'active' : '') + '">EN</button></div>' +
      '<span class="v631p-user">' + esc(userName()) + '</span></div></header>';
  }

  function scenarioHTML(language, data) {
    const chinese = language !== 'english';
    return '<section class="v631p-live" aria-label="Рабочий сценарий">' +
      '<div class="v631p-live-meta"><span>LIVE SCENARIO · ' + (chinese ? 'SUPPLIER CALL' : 'PRODUCTION CALL') + '</span><time>' + new Date().toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}) + '</time></div>' +
      (chinese ? '<h2 lang="zh-CN">' + esc(data.cn) + '</h2><p class="v631p-pinyin">' + esc(data.pinyin) + '</p>' : '<h2 class="v631p-live-en">' + esc(data.en) + '</h2>') +
      '<p class="v631p-translation">' + esc(data.ru) + '</p>' +
      '<div class="v631p-scenario-actions">' +
      '<button data-v631-target="roleplay"><span>A</span><b>Ответить</b></button>' +
      '<button class="selected" data-v631-target="roleplay"><span>B</span><b>Уточнить</b></button>' +
      '<button data-v631-target="roleplay"><span>C</span><b>Согласовать срок</b></button></div></section>';
  }

  function timelineHTML() {
    const steps = [
      ['01','Сборка'],['02','Сварка'],['03','Окраска'],['04','Качество'],['05','Логистика']
    ];
    return '<section class="v631p-line"><div class="v631p-section-label">ЛИНИЯ ОБУЧЕНИЯ</div><div class="v631p-line-grid">' +
      steps.map(function (step, index) {
        return '<button data-v631-target="topics" class="' + (index === 1 ? 'current' : '') + '"><small>' + step[0] + '</small><b>' + esc(step[1]) + '</b><i></i></button>';
      }).join('') + '</div></section>';
  }

  function todayHTML(language, data) {
    const p = progress();
    const terms = data.terms || [];
    return '<section class="v631p-today">' +
      '<div class="v631p-today-intro"><span>СЕГОДНЯ</span><h2>Одна реальная<br>ситуация. До конца.</h2><div class="v631p-day"><b>' + String(p.day).padStart(2,'0') + '</b><em>/ 30</em><small>день курса</small></div></div>' +
      '<div class="v631p-today-mission"><span>СИТУАЦИЯ ДНЯ</span><h3>' + esc(data.title) + '</h3><small>Цель</small><p>' + esc(data.goal) + '</p>' +
      '<button class="v631p-primary" data-v631-target="roleplay">Войти в ситуацию <span>→</span></button></div>' +
      '<div class="v631p-terms"><span>КЛЮЧЕВЫЕ ФРАЗЫ</span>' + terms.map(function (term) {
        return '<button data-v631-target="topics"><b>' + esc(term[0]) + '</b><small>' + esc(term[1]) + '</small></button>';
      }).join('') + '</div></section>';
  }

  function modulesHTML() {
    const items = [
      ['01','Сценарии','5–8 минут','roleplay'],
      ['02','Игры','3 минуты','games'],
      ['03','Тест','10 вопросов','quiz'],
      ['04','Итоговый экзамен','по готовности','exam']
    ];
    return '<section class="v631p-next"><div class="v631p-section-label">ДАЛЬШЕ</div><div class="v631p-next-grid">' + items.map(function (item) {
      return '<button data-v631-target="' + item[3] + '"><small>' + item[0] + '</small><b>' + esc(item[1]) + '</b><span>' + esc(item[2]) + '</span><em>→</em></button>';
    }).join('') + '</div></section>';
  }

  function render() {
    const snap = current();
    const language = snap.language === 'english' ? 'english' : 'chinese';
    const data = mission(language);
    const main = document.getElementById('main');
    if (!main) throw new Error('premium-home missing #main');

    state().set('view', 'home');
    document.body.classList.add('v631-premium-home-active');
    main.innerHTML = '<div class="v631p-home">' + headerHTML(language) +
      '<main class="v631p-canvas"><section class="v631p-hero"><div class="v631p-hero-copy"><span>ЯЗЫК = РАБОЧИЙ ИНСТРУМЕНТ</span>' +
      '<h1>Говори на языке<br>производства.</h1><p>Не учим «по учебнику». Тренируем именно то, что нужно на встрече, в цехе и при работе с поставщиком.</p>' +
      '<div><button class="v631p-primary" data-v631-target="roleplay">Начать смену <span>→</span></button><small>12 минут · персональный маршрут</small></div></div>' +
      scenarioHTML(language, data) + '</section>' + timelineHTML() + todayHTML(language, data) + modulesHTML() +
      '<footer class="v631p-footer"><span>MGC GROUP · AUTOMOTIVE LANGUAGE TRAINING</span><span>Company Pilot</span></footer></main></div>';

    bindActions();
    return true;
  }

  function bindActions() {
    document.querySelectorAll('[data-v631-target]').forEach(function (button) {
      button.addEventListener('click', function () {
        const target = button.getAttribute('data-v631-target') || 'home';
        Promise.resolve(nav().setView(target)).catch(function (error) {
          if (frontend.has('error-boundary')) frontend.get('error-boundary').record('premium-home-navigation', error && error.message ? error.message : error, '', 0, 0);
        });
      });
    });

    document.querySelectorAll('[data-v631-language]').forEach(function (button) {
      button.addEventListener('click', function () {
        const language = button.getAttribute('data-v631-language');
        const source = document.querySelector('.language-switch [data-language="' + language + '"]');
        if (source) {
          source.click();
          root.setTimeout(function () { render(); }, 120);
        } else {
          state().set('language', language);
          render();
        }
      });
    });
  }

  function navigate(view) {
    if (!owns(view)) return false;
    return render();
  }

  frontend.register('premium-home', {
    views: Object.freeze(['home']),
    owns: owns,
    render: render,
    navigate: navigate
  });
})(typeof window !== 'undefined' ? window : globalThis);
