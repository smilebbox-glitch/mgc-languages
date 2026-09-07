/* v6.0.7: canonical ownership for the final assessment view. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('final-assessment')) return;

  const OWNED_VIEWS = Object.freeze(['exam']);
  const owned = new Set(OWNED_VIEWS);
  const EXAM_TOTAL = 50;
  const PASS_SCORE = 35;
  let installed = false;

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function api() { return frontend.get('api-client'); }

  function owns(view) {
    return owned.has(String(view || ''));
  }

  function reportError(scope, error) {
    if (!frontend.has('error-boundary')) return;
    frontend.get('error-boundary').record(
      String(scope || 'final-assessment'),
      error && error.message ? error.message : error,
      '', 0, 0
    );
  }

  function pageHead(kicker, title, subtitle) {
    const esc = legacy().escapeHtml;
    return '<div class="page-head"><div><div class="kicker">' + esc(kicker) +
      '</div><h1>' + esc(title) + '</h1><p>' + esc(subtitle) + '</p></div></div>';
  }

  function renderIntro() {
    const main = legacy().query('#main');
    if (!main) throw new Error('Final assessment view missing #main');
    main.innerHTML = pageHead(
      'Итоговая проверка',
      'Финальный экзамен',
      '50 вопросов от A1 до C1. Экзамен сдан при результате 35/50 или выше.'
    ) + '<div class="card exam-intro"><h2>Проверка всей программы</h2><div class="exam-levels">' +
      ['A1 · 10', 'A2 · 10', 'B1 · 10', 'B2 · 10', 'C1 · 10'].map(function (item) {
        return '<span>' + item + '</span>';
      }).join('') +
      '</div><p>Перевод, обратный перевод, рабочий контекст и выбор точной формулировки. Для китайского pinyin отображается в каждом вопросе.</p>' +
      '<div class="pass-rule">Проходной результат <b>35 из 50</b></div><button id="startExam" class="primary">Начать экзамен</button></div>';
    const start = legacy().query('#startExam');
    if (start) start.addEventListener('click', function () { void startExam(); });
  }

  function renderResult(current) {
    const main = legacy().query('#main');
    if (!main) throw new Error('Final assessment view missing #main');
    const score = Number(current.examScore || 0);
    const passed = score >= PASS_SCORE;
    const percent = Math.round(score * 2);
    main.innerHTML = pageHead(
      'Экзамен завершён',
      passed ? 'Экзамен сдан' : 'Экзамен пока не сдан',
      passed ? 'Вы преодолели порог 35/50.' : 'Повторите слабые темы и попробуйте снова.'
    ) + '<div class="card exam-intro ' + (passed ? 'exam-pass' : 'exam-retry') + '"><div class="result-score">' +
      score + '/50</div><p>' + percent + '% правильных ответов</p><button id="restartExam" class="primary">Пройти заново</button></div>';
    const restart = legacy().query('#restartExam');
    if (restart) {
      restart.addEventListener('click', function () {
        state().patch({exam: null, examIndex: 0, examScore: 0, examAnswered: false});
        void render();
      });
    }
  }

  function renderQuestion(current) {
    const main = legacy().query('#main');
    if (!main) throw new Error('Final assessment view missing #main');
    const esc = legacy().escapeHtml;
    const exam = Array.isArray(current.exam) ? current.exam : [];
    const examIndex = Number(current.examIndex || 0);
    const question = exam[examIndex];
    if (!question) throw new Error('Final assessment question is missing');
    const options = Array.isArray(question.options) ? question.options : [];

    main.innerHTML = '<div class="quiz-stage"><div class="exam-score-live">Правильно: <b>' + Number(current.examScore || 0) +
      '</b></div><div class="quiz-progress"><i style="width:' + ((examIndex + 1) * 2) + '%"></i></div>' +
      '<div class="card question-card"><div class="kicker">' + esc(question.level + ' · вопрос ' + (examIndex + 1) + ' из 50') +
      '</div><h2>' + esc(question.prompt) + '</h2>' +
      (question.pronunciation ? '<div class="question-pinyin">' + esc(question.pronunciation) + '</div>' : '') +
      '<div class="options">' + options.map(function (option, index) {
        return '<button class="option" data-exam-answer="' + index + '">' + esc(option) + '</button>';
      }).join('') + '</div><div id="examNextWrap"></div></div></div>';

    legacy().queryAll('[data-exam-answer]').forEach(function (button) {
      button.addEventListener('click', function () { answerExam(Number(button.dataset.examAnswer)); });
    });
  }

  async function render() {
    const current = state().current();
    const exam = Array.isArray(current.exam) ? current.exam : null;
    if (!exam) {
      renderIntro();
      return;
    }
    if (Number(current.examIndex || 0) >= exam.length) {
      renderResult(current);
      return;
    }
    renderQuestion(current);
  }

  async function startExam() {
    const current = state().current();
    try {
      const data = await api().request('/api/language/' + encodeURIComponent(current.language) + '/final-exam');
      state().patch({
        exam: data && Array.isArray(data.questions) ? data.questions : [],
        examIndex: 0,
        examScore: 0,
        examAnswered: false
      });
      await render();
    } catch (error) {
      reportError('final-assessment-start', error);
      throw error;
    }
  }

  function answerExam(index) {
    const current = state().current();
    if (current.examAnswered) return;
    const exam = Array.isArray(current.exam) ? current.exam : [];
    const examIndex = Number(current.examIndex || 0);
    const question = exam[examIndex];
    if (!question) return;

    const correct = index === Number(question.correct_index);
    state().patch({
      examAnswered: true,
      examScore: Number(current.examScore || 0) + (correct ? 1 : 0)
    });

    legacy().queryAll('[data-exam-answer]').forEach(function (button) {
      const value = Number(button.dataset.examAnswer);
      if (value === Number(question.correct_index)) button.classList.add('correct');
      else if (value === index) button.classList.add('wrong');
      button.disabled = true;
    });

    const wrap = legacy().query('#examNextWrap');
    if (!wrap) return;
    const options = Array.isArray(question.options) ? question.options : [];
    wrap.innerHTML = '<div class="answer-feedback"><b>' +
      (correct ? 'Верно' : 'Правильный ответ: ' + legacy().escapeHtml(options[question.correct_index])) +
      '</b><p>' + legacy().escapeHtml(question.explanation || '') + '</p></div>' +
      '<button id="examNext" class="primary wide">' + (examIndex === 49 ? 'Завершить экзамен' : 'Следующий вопрос') + '</button>';
    const next = legacy().query('#examNext');
    if (next) next.addEventListener('click', function () { void advanceExam(); });
  }

  async function advanceExam() {
    const current = state().current();
    const nextIndex = Number(current.examIndex || 0) + 1;
    state().patch({examIndex: nextIndex, examAnswered: false});

    if (nextIndex === EXAM_TOTAL) {
      const latest = state().current();
      try {
        await api().request('/api/final-exam/result', {
          method: 'POST',
          body: JSON.stringify({
            language: latest.language,
            score: Number(latest.examScore || 0),
            total: EXAM_TOTAL,
            answers: []
          })
        });
        await legacy().submitPractice(
          'exam',
          legacy().newSessionId('exam-' + latest.language),
          Number(latest.examScore || 0),
          EXAM_TOTAL,
          'Final Exam'
        );
        const summary = await api().request('/api/language/' + encodeURIComponent(latest.language) + '/summary');
        state().set('summary', summary);
      } catch (error) {
        reportError('final-assessment-submit', error);
      }
    }
    await render();
  }

  async function navigate(view) {
    const target = String(view || 'exam');
    if (!owns(target)) return legacy().setView(target);

    state().set('view', target);
    legacy().closeMenu();
    legacy().queryAll('[data-view]').forEach(function (button) {
      button.classList.toggle('active', button.dataset.view === target);
    });
    const main = legacy().query('#main');
    if (main) main.innerHTML = '<div class="loading-card"><span class="spinner"></span><p>Загрузка</p></div>';

    try {
      await render();
    } catch (error) {
      if (main) {
        main.innerHTML = '<div class="empty"><h2>Не удалось открыть экзамен</h2><p>' +
          legacy().escapeHtml(error && error.message ? error.message : error) +
          '</p><button class="primary" data-go="home">На главную</button></div>';
      }
      reportError('final-assessment-navigation', error);
      throw error;
    }
  }

  function install() {
    if (installed) return;
    installed = true;
    document.addEventListener('click', function (event) {
      const button = event.target && event.target.closest ? event.target.closest('[data-view]') : null;
      if (!button || !owns(button.dataset.view)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      navigate(button.dataset.view).catch(function () {});
    }, true);
  }

  frontend.register('final-assessment', {
    views: OWNED_VIEWS,
    owns: owns,
    render: render,
    navigate: navigate,
    startExam: startExam,
    answerExam: answerExam,
    advanceExam: advanceExam,
    install: install
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install, {once: true});
  } else {
    install();
  }
})(typeof window !== 'undefined' ? window : globalThis);
