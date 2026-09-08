# v6.0.22 — Production Decision Chains

## Что изменилось

Языковая аркада получила многошаговые производственные решения поверх существующих 20 игр.

- На уровнях **Смена** и **Эксперт** основная языковая задача может быть заблокирована до прохождения трёх последовательных производственных решений.
- В адаптивном режиме первые два вопроса остаются учебными, а вопросы 3–5 получают сменную/экспертную логику из v6.0.21.
- Неправильный выбор не просто помечается как ошибка: пользователь видит конкретное производственное последствие.
- После каждого решения показывается полезная рабочая фраза на изучаемом языке:
  - Chinese: иероглифы + pinyin + русский смысл;
  - English: shop-floor формулировка + русский смысл.
- Добавлен отдельный локальный показатель **Production judgement**. Он не начисляет XP и не создаёт второй путь фарма.

## Цепочки решений

1. **Andon / Line Stop** — stop risk → containment → verified restart.
2. **Quality Escalation** — containment → traceability → root cause / corrective action.
3. **Material Shortage** — run-out → recovery route → ETA / owner.
4. **Body Shop Containment** — suspect body → welding parameters / fixture → verified restart.
5. **Paint Process Recovery** — hold → process parameter check → first-off confirmation.
6. **Safety Near Miss** — stop exposure → restore barrier → verified restart.
7. **Engineering Change** — scope → downstream impact → controlled release.
8. **Supplier Escalation** — facts → containment → owner / deadline / evidence.

## Техническая интеграция

Новый слой использует API `game-depth-v621` для определения эффективной сложности и производственной сцены. Backend game engine, пятиответный контракт, XP и anti-farm не изменялись.

Файлы:

```text
static/frontend/decision_chains_v622.js
static/decision_chains_v622.css
tests/v622_decision_chains_test.py
BUILD_INFO_v6.0.22.txt
```
