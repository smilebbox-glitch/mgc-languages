# v6.0.28 — UX / Accessibility / Performance Polish

## Цель релиза

v6.0.28 не добавляет новую игровую механику. Релиз стабилизирует пилот перед freeze: упрощает взаимодействие с интерфейсом, улучшает клавиатурную и screen-reader доступность и уменьшает лишнюю работу браузера на динамических экранах.

## Accessibility

- статический skip-link «Перейти к основному содержанию»;
- `main` доступен как отдельная focus-target область;
- sidebar обозначен как основная навигация;
- menu toggle синхронизирует `aria-expanded`;
- активный пункт меню получает `aria-current="page"`;
- переключатели языка и Pinyin синхронизируют `aria-pressed`;
- login/register tabs получают `aria-selected` и клавиатурное переключение стрелками;
- toast и результаты игр используют polite live-region semantics;
- при переходе между разделами screen reader получает короткое объявление;
- фокус переносится на заголовок нового раздела, но не перехватывается у пользователя во время ввода.

## Keyboard UX

- `Esc` закрывает открытое мобильное меню и возвращает фокус на кнопку меню;
- `/` переводит фокус в поиск по темам, если пользователь сейчас не вводит текст;
- стрелки Left/Right переключают вкладки Вход / Регистрация.

## Motion / contrast

CSS учитывает:

- `prefers-reduced-motion: reduce`;
- `forced-colors: active`;
- единый заметный `:focus-visible`;
- touch-friendly минимальную высоту основных мобильных nav/auth controls.

## Performance

Старый `pilot_ux_hardening.js` больше не запускает полный `applyDomFixes(document)` на каждую DOM mutation.

Теперь:

1. observer собирает только реально добавленные element roots;
2. roots складываются в bounded-per-frame Set;
3. обработка выполняется один раз через `requestAnimationFrame`;
4. полный document scan остаётся только при первоначальной установке модуля.

Нижние тяжёлые блоки Shift Simulation / Top-10 / Adaptive Training получают `content-visibility:auto`, чтобы браузер мог пропускать offscreen layout/paint до момента, когда блок приблизится к viewport.

## Архитектурные ограничения

- backend API не меняется;
- новых database migrations нет;
- новых XP endpoints нет;
- max-5 game-session contract не меняется;
- anti-farm не меняется;
- Adaptive Training v6.0.27 и все предыдущие производственные сценарии остаются совместимыми.

## Основные файлы

```text
static/frontend/ux_performance_v628.js
static/ux_performance_v628.css
static/frontend/pilot_ux_hardening.js
tests/v628_ux_performance_test.py
.github/workflows/ci-v628-ux-performance.yml
```
