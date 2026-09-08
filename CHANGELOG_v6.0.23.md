# v6.0.23 — Dynamic Factory Scenarios

## Что изменилось

Производственные решения из v6.0.22 теперь меняют состояние следующего шага, а не заканчиваются локальным right/wrong feedback.

- Добавлен **Live Factory State** для уровней Смена и Эксперт.
- Состояние переносится между шагами одной производственной цепочки.
- Неправильные решения могут:
  - увеличить число автомобилей/кузовов в suspect window;
  - повысить риск повторного line stop;
  - сократить доступное время до material run-out;
  - ухудшить readiness к restart;
  - увеличить конфигурационный риск engineering change;
  - ухудшить ясность и качество supplier response.
- Правильные решения постепенно повышают containment, evidence, recovery control и restart readiness.
- Следующий шаг получает отдельный блок **«Состояние после предыдущего решения»**.
- История последних решений отображается как короткая timeline последствий.

## Supplier Dialogue

Для эскалации китайскому поставщику ответ теперь зависит от качества предыдущей реплики.

- Размытая или обвинительная формулировка приводит к запросу номера детали, партии и конкретного дефекта.
- Точный запрос с part/lot/quantity позволяет сразу перейти к traceability.
- Хороший containment-запрос приводит к подтверждённому stock isolation / sorting / ETA.
- Финальная эскалация с owner/deadline/evidence формирует измеримый ответ поставщика.
- В китайском режиме показываются иероглифы + pinyin + русский смысл; в английском — English + русский смысл.

## Семейства динамических сценариев

1. Andon / Line Stop.
2. Quality containment.
3. Material shortage.
4. Body Shop / welding.
5. Paint recovery.
6. Safety near miss.
7. Engineering change.
8. Supplier escalation.

## XP и backend

Dynamic Factory Scenarios — клиентский обучающий слой поверх существующего game engine.

- новые XP endpoints не добавлялись;
- серверный лимит пяти ответов не менялся;
- anti-farm не менялся;
- существующие игровые API не дублируются.

## Файлы

```text
static/frontend/dynamic_factory_v623.js
static/dynamic_factory_v623.css
tests/v623_dynamic_factory_test.py
BUILD_INFO_v6.0.23.txt
```
