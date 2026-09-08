/* v6.0.24: full-shift simulation with prioritization, linked incidents, bilingual communication and end-of-shift review. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("shift-simulation-v624")) return;

  let installed = false;
  let observer = null;
  let scheduled = false;
  let run = null;

  const METRICS = Object.freeze([
    {key:"line", label:"Стабильность линии", bad:"low"},
    {key:"quality", label:"Защита качества", bad:"low"},
    {key:"material", label:"Material runway", bad:"low"},
    {key:"supplier", label:"Supplier control", bad:"low"},
    {key:"load", label:"Нагрузка команды", bad:"high"}
  ]);

  function A(label, correct, impact, outcome, flag) {
    return {label:label, correct:Boolean(correct), impact:impact || {}, outcome:outcome, flag:flag || null};
  }

  function M(score, zh, pinyin, en, ru, feedback) {
    return {score:Number(score), zh:zh, pinyin:pinyin, en:en, ru:ru, feedback:feedback};
  }

  const INCIDENTS = Object.freeze({
    paint_repeat: {
      id:"paint_repeat", area:"Окраска / качество", title:"Повторяемый дефект покрытия", priority:5,
      summary:"На трёх кузовах подряд найден повторяемый surface defect. Следующая партия уже входит в booth exit.",
      evidence:["3 кузова подряд", "один цвет / одна камера", "граница дефекта не доказана"],
      delayImpact:{quality:-14, line:-5, load:8}, delayText:"Без раннего containment suspect window расширился ещё на несколько кузовов.",
      actions:[
        A("Hold затронутые кузова, определить last known good и открыть containment", true, {quality:14, line:-2, load:4}, "Дефект локализован до дальнейшего распространения.", "paintContained"),
        A("Продолжить выпуск до планового break, затем проверить всю партию", false, {quality:-16, line:-4, load:8}, "К концу окна проверки объём сортировки вырос.", null),
        A("Сразу отправить все кузова на полировку без классификации дефекта", false, {quality:-8, load:12}, "Rework скрывает симптом и ухудшает доказательность root cause.", null)
      ],
      messages:[
        M(2, "请先扣留受影响的车身，并确认最后一个合格车身。", "Qǐng xiān kòuliú shòu yǐngxiǎng de chēshēn, bìng quèrèn zuìhòu yí ge hégé chēshēn.", "Please hold the affected bodies and confirm the last known good body.", "Сначала удержите затронутые кузова и подтвердите последний заведомо годный кузов.", "Фраза задаёт конкретный containment и границу."),
        M(1, "请检查一下油漆问题。", "Qǐng jiǎnchá yíxià yóuqī wèntí.", "Please check the paint issue.", "Пожалуйста, проверьте проблему с окраской.", "Понятно, но нет масштаба, границы и требуемого действия."),
        M(0, "油漆又有问题了。", "Yóuqī yòu yǒu wèntí le.", "Paint has a problem again.", "С окраской опять проблема.", "Эмоциональная формулировка не управляет процессом.")
      ]
    },
    supplier_delay: {
      id:"supplier_delay", area:"Логистика / Китай", title:"Задержка критичного компонента", priority:5,
      summary:"Китайский поставщик сообщил, что грузовик с критичным компонентом задерживается. Точный ETA отсутствует.",
      evidence:["остаток на линии: 78 мин", "2 модели используют компонент", "ETA поставщика не подтверждён"],
      delayImpact:{material:-18, supplier:-8, line:-5, load:5}, delayText:"Без recovery plan запас до run-out заметно сократился.",
      actions:[
        A("Пересчитать stock/run-out, запросить expedite/alternative route и назначить owner", true, {material:12, supplier:10, load:4}, "Recovery стал измеримым, у команды появилось управляемое окно.", "supplierExpedite"),
        A("Ждать плановую машину и проверять статус раз в час", false, {material:-20, supplier:-6, line:-7}, "Окно до run-out потеряно без активного recovery.", null),
        A("Разрешить похожий компонент со склада без ECN/approval", false, {quality:-12, supplier:-4, line:-4, load:10}, "Логистический риск превратился ещё и в конфигурационный/quality risk.", "unapprovedSubstitution")
      ],
      messages:[
        M(2, "请确认现有库存、预计断料时间、加急方案和最晚到达时间。", "Qǐng quèrèn xiànyǒu kùcún, yùjì duànliào shíjiān, jiājí fāng'àn hé zuìwǎn dàodá shíjiān.", "Please confirm current stock, expected run-out, the expedite plan, and the latest committed arrival time.", "Подтвердите текущий запас, ожидаемый run-out, expedite-план и крайнее подтверждённое время прибытия.", "Запрос содержит факты, срок и recovery."),
        M(1, "请尽快发货。", "Qǐng jǐnkuài fāhuò.", "Please ship as soon as possible.", "Отправьте как можно скорее.", "Срочность есть, но нет quantity/ETA/owner."),
        M(0, "这个延误不能接受。", "Zhège yánwù bù néng jiēshòu.", "This delay is unacceptable.", "Эта задержка неприемлема.", "Оценка без конкретного запроса не создаёт recovery plan.")
      ]
    },
    torque_alarm: {
      id:"torque_alarm", area:"Сборка / производство", title:"Повторный torque alarm", priority:4,
      summary:"На станции финальной сборки повторился torque alarm. Оператор сбросил первый alarm, но второй автомобиль снова остановлен.",
      evidence:["2 повторения за 12 мин", "один инструмент", "следующий автомобиль уже в буфере"],
      delayImpact:{line:-10, quality:-7, load:6}, delayText:"Повторный alarm без проверки инструмента увеличил очередь и quality risk.",
      actions:[
        A("Andon, stop risk, quarantine suspect operations, проверить tool/program и first-off", true, {line:6, quality:12, load:5}, "Риск изолирован до выпуска следующего автомобиля.", "torqueProtected"),
        A("Ещё раз сбросить alarm и продолжить до третьего повторения", false, {line:-12, quality:-14, load:8}, "Следующий автомобиль получил тот же риск, а evidence стало слабее.", null),
        A("Сразу заменить оператора без проверки оборудования", false, {line:-6, quality:-5, load:12}, "Причина не локализована, команда получила лишнюю нагрузку.", null)
      ],
      messages:[
        M(2, "请停止该工位，并确认工具程序、扭矩记录和首件结果。", "Qǐng tíngzhǐ gāi gōngwèi, bìng quèrèn gōngjù chéngxù, niǔjǔ jìlù hé shǒujiàn jiéguǒ.", "Stop the station and confirm the tool program, torque trace, and first-off result.", "Остановите пост и подтвердите программу инструмента, torque trace и результат first-off.", "Фраза связывает stop, evidence и restart gate."),
        M(1, "请检查扭矩工具。", "Qǐng jiǎnchá niǔjǔ gōngjù.", "Please check the torque tool.", "Проверьте torque tool.", "Технически понятно, но нет containment и restart criteria."),
        M(0, "工具又坏了。", "Gōngjù yòu huài le.", "The tool is broken again.", "Инструмент опять сломан.", "Причина утверждается без подтверждения.")
      ]
    },
    paint_spread: {
      id:"paint_spread", area:"Окраска / качество", title:"Suspect window расширился", priority:5,
      summary:"После утреннего дефекта в зоне проверки уже несколько кузовов. Нужно определить границу и восстановить process evidence.",
      evidence:["растущий suspect window", "booth параметры доступны", "rework очередь увеличивается"],
      delayImpact:{quality:-12, load:10, line:-4}, delayText:"Каждая задержка увеличивает сортировку и rework backlog.",
      actions:[
        A("Traceability по времени/цвету/booth, параметры процесса, first-off после коррекции", true, {quality:16, line:3, load:-3}, "Граница и process evidence восстановлены.", "paintRecovered"),
        A("Сортировать только визуально без временной границы", false, {quality:-7, load:8}, "Сортировка защищает часть продукта, но граница остаётся предположением.", null),
        A("Снизить критерий поверхности до конца смены", false, {quality:-18, load:2}, "Критерий изменён без инженерного основания.", null)
      ],
      messages:[
        M(2, "请确认喷房参数、受影响时间窗口和修正后的首件结果。", "Qǐng quèrèn pēnfáng cānshù, shòu yǐngxiǎng shíjiān chuāngkǒu hé xiūzhèng hòu de shǒujiàn jiéguǒ.", "Confirm booth parameters, the affected time window, and the corrected first-off result.", "Подтвердите параметры камеры, затронутое временное окно и результат first-off после коррекции.", "Запрос строит traceability и evidence."),
        M(1, "请再检查几台车。", "Qǐng zài jiǎnchá jǐ tái chē.", "Please check a few more vehicles.", "Проверьте ещё несколько автомобилей.", "Не определены граница и критерий завершения."),
        M(0, "先别管，后面再说。", "Xiān bié guǎn, hòumiàn zài shuō.", "Leave it for now; we will discuss it later.", "Пока не трогайте, разберёмся потом.", "Фраза прямо увеличивает производственный риск.")
      ]
    },
    material_runout: {
      id:"material_runout", area:"Логистика / производство", title:"Run-out приблизился к line stop", priority:5,
      summary:"Остаток критичного компонента быстро снижается. Требуется реальный recovery, а не просто новый статус.",
      evidence:["run-out < 55 мин", "часть stock можно перераспределить", "поставщик на связи"],
      delayImpact:{material:-20, line:-10, load:8}, delayText:"Запас ушёл в критическую зону, производственная гибкость сократилась.",
      actions:[
        A("Приоритизировать модели, подтвердить approved stock, expedite ETA и fallback", true, {material:18, line:8, supplier:8, load:4}, "Команда защитила линию несколькими recovery-рычагами.", "materialProtected"),
        A("Остановить все модели сразу, не проверяя потребление", false, {line:-15, material:3, load:10}, "Создана лишняя потеря производства без расчёта.", null),
        A("Переместить неутверждённый stock на линию", false, {quality:-15, material:6, load:9}, "Material recovery породил quality/configuration risk.", "unapprovedSubstitution")
      ],
      messages:[
        M(2, "请确认可用合格库存、车型优先级、加急到达时间和备用方案。", "Qǐng quèrèn kěyòng hégé kùcún, chēxíng yōuxiānjí, jiājí dàodá shíjiān hé bèiyòng fāng'àn.", "Confirm approved stock, model priority, expedite ETA, and the fallback plan.", "Подтвердите утверждённый запас, приоритет моделей, expedite ETA и fallback.", "Формулировка поддерживает recovery cadence."),
        M(1, "现在库存不够。", "Xiànzài kùcún bú gòu.", "We do not have enough stock now.", "Сейчас запаса недостаточно.", "Факт сообщён, но действия и срок не определены."),
        M(0, "你们必须马上解决。", "Nǐmen bìxū mǎshàng jiějué.", "You must solve this immediately.", "Вы должны немедленно это решить.", "Давление без данных не ускоряет recovery.")
      ]
    },
    quality_gate_hold: {
      id:"quality_gate_hold", area:"Качество / сборка", title:"Quality Gate удержал автомобили", priority:5,
      summary:"Torque trace по части автомобилей неполон. Quality Gate не может подтвердить соответствие без дополнительной проверки.",
      evidence:["trace gap", "3 автомобиля в hold", "инструмент уже проверяется"],
      delayImpact:{quality:-10, line:-8, load:8}, delayText:"Hold растёт, а evidence всё ещё неполное.",
      actions:[
        A("Определить affected VIN/time window, проверить torque evidence и disposition каждого авто", true, {quality:15, line:4, load:4}, "Hold превратился в управляемый containment.", "qualityTraceRestored"),
        A("Выпустить автомобили по визуальной проверке", false, {quality:-20, line:3}, "Визуальная проверка не заменяет torque evidence.", null),
        A("Оставить все автомобили в hold до конца смены без owner", false, {line:-10, load:12}, "Containment есть, но нет управляемого решения.", null)
      ],
      messages:[
        M(2, "请确认受影响车辆范围、扭矩追溯记录和每台车的处置结果。", "Qǐng quèrèn shòu yǐngxiǎng chēliàng fànwéi, niǔjǔ zhuīsù jìlù hé měi tái chē de chǔzhì jiéguǒ.", "Confirm the affected vehicle scope, torque trace records, and disposition for each vehicle.", "Подтвердите диапазон затронутых автомобилей, torque trace и disposition каждого автомобиля.", "Язык точно описывает quality containment."),
        M(1, "这些车需要再检查。", "Zhèxiē chē xūyào zài jiǎnchá.", "These vehicles need another check.", "Эти автомобили нужно проверить ещё раз.", "Не указаны evidence и критерий release."),
        M(0, "应该没问题，可以放行。", "Yīnggāi méi wèntí, kěyǐ fàngxíng.", "They should be fine; we can release them.", "Наверное, всё нормально, можно выпускать.", "Предположение вместо evidence.")
      ]
    },
    weld_drift: {
      id:"weld_drift", area:"Сварка / кузов", title:"Geometry drift на body shop", priority:4,
      summary:"Контроль геометрии показывает дрейф по одной точке кузова. Робот не alarm-ит, но trend ухудшается.",
      evidence:["3 измерения с трендом", "robot OK", "fixture/electrode ещё не проверены"],
      delayImpact:{quality:-9, line:-5, load:5}, delayText:"Trend продолжил ухудшаться и затронул дополнительные кузова.",
      actions:[
        A("Contain suspect bodies, проверить fixture/электроды/параметры и first-off", true, {quality:12, line:4, load:5}, "Дрейф локализован до структурного дефекта.", "weldContained"),
        A("Ждать выхода за допуск", false, {quality:-13, line:-5}, "Тренд проигнорирован до фактического NOK.", null),
        A("Компенсировать геометрию ручной правкой без анализа", false, {quality:-9, load:10}, "Симптом скорректирован без устранения причины.", null)
      ],
      messages:[
        M(2, "请隔离可疑车身，并检查夹具、电极和焊接参数趋势。", "Qǐng gélí kěyí chēshēn, bìng jiǎnchá jiājù, diànjí hé hànjiē cānshù qūshì.", "Contain the suspect bodies and check the fixture, electrodes, and welding parameter trend.", "Изолируйте подозрительные кузова и проверьте fixture, электроды и тренд параметров сварки.", "Фраза соответствует body-shop problem solving."),
        M(1, "请检查焊接。", "Qǐng jiǎnchá hànjiē.", "Please check welding.", "Проверьте сварку.", "Слишком широко для оперативной локализации."),
        M(0, "机器人没有报警，所以没问题。", "Jīqìrén méiyǒu bàojǐng, suǒyǐ méi wèntí.", "The robot has no alarm, so there is no problem.", "У робота нет alarm, значит проблемы нет.", "Alarm status не заменяет product evidence.")
      ]
    },
    engineering_substitution: {
      id:"engineering_substitution", area:"R&D / закупки / логистика", title:"Предложена временная замена детали", priority:5,
      summary:"Из-за дефицита поставщик предлагает похожую ревизию детали. Физически она подходит, но effective point и approval отсутствуют.",
      evidence:["другая revision", "BOM не обновлён", "сертификационный/quality impact не оценён"],
      delayImpact:{material:-8, quality:-8, load:7}, delayText:"Дефицит сохраняется, а давление на неуправляемую замену растёт.",
      actions:[
        A("Открыть controlled engineering change: scope, BOM/WI/quality impact, approval, effective point", true, {quality:10, material:8, supplier:5, load:6}, "Замена переведена в управляемый change-control процесс.", "ecnControlled"),
        A("Разрешить замену устно на одну смену", false, {quality:-18, line:-4, load:10}, "Конфигурационный риск ушёл прямо в производство.", "unapprovedSubstitution"),
        A("Отклонить вариант без проверки и просто ждать исходную деталь", false, {material:-15, line:-8}, "Без оценки альтернативы потеряно потенциальное recovery-окно.", null)
      ],
      messages:[
        M(2, "请提供替代零件版本、差异、影响评估和建议生效点，批准前不要上线。", "Qǐng tígōng tìdài língjiàn bǎnběn, chāyì, yǐngxiǎng pínggū hé jiànyì shēngxiào diǎn, pīzhǔn qián búyào shàngxiàn.", "Provide the substitute revision, differences, impact assessment, and proposed effective point. Do not use it before approval.", "Предоставьте revision замены, различия, оценку влияния и предлагаемый effective point. Не используйте до approval.", "Фраза фиксирует change-control gate."),
        M(1, "这个零件看起来可以用。", "Zhège língjiàn kàn qǐlái kěyǐ yòng.", "This part looks usable.", "Эта деталь выглядит подходящей.", "Визуальная применимость не равна engineering approval."),
        M(0, "先用，文件以后再改。", "Xiān yòng, wénjiàn yǐhòu zài gǎi.", "Use it first; update the documents later.", "Сначала используем, документы исправим потом.", "Это прямой источник configuration escape.")
      ]
    },
    supplier_traceability: {
      id:"supplier_traceability", area:"Китай / качество", title:"Поставщик прислал неполный containment", priority:4,
      summary:"Поставщик подтвердил сортировку, но не указал lot range, certified quantity и доказательство проверки.",
      evidence:["sorting заявлен", "lot range отсутствует", "ETA есть, evidence нет"],
      delayImpact:{supplier:-10, quality:-5, load:6}, delayText:"Без traceability доверие к следующей поставке снизилось.",
      actions:[
        A("Запросить lot range, sorted quantity, criteria, evidence и shipment ID", true, {supplier:15, quality:7, load:3}, "Supplier containment стал проверяемым.", "supplierTraceability"),
        A("Принять письмо как достаточное подтверждение", false, {supplier:-12, quality:-10}, "Поставка остаётся с неясной границей риска.", null),
        A("Потребовать только 8D, не закрывая текущую поставку", false, {supplier:-5, material:-6, load:5}, "Долгосрочный анализ не заменил оперативный containment.", null)
      ],
      messages:[
        M(2, "请补充批次范围、筛选数量、判定标准、验证记录和发运编号。", "Qǐng bǔchōng pīcì fànwéi, shāixuǎn shùliàng, pàndìng biāozhǔn, yànzhèng jìlù hé fāyùn biānhào.", "Please add the lot range, sorted quantity, acceptance criteria, verification records, and shipment ID.", "Добавьте диапазон партии, количество после сортировки, критерий приемки, записи проверки и shipment ID.", "Запрос превращает обещание в evidence."),
        M(1, "请发更多信息。", "Qǐng fā gèng duō xìnxī.", "Please send more information.", "Пришлите больше информации.", "Непонятно, какие данные нужны."),
        M(0, "你们的回复不够好。", "Nǐmen de huífù bú gòu hǎo.", "Your response is not good enough.", "Ваш ответ недостаточно хороший.", "Оценка не задаёт критерий закрытия.")
      ]
    },
    line_stop: {
      id:"line_stop", area:"Производство / качество", title:"Line stop из-за накопленных рисков", priority:5,
      summary:"Несколько открытых рисков сошлись на линии. Требуется решить, что защищать первым и как восстановить controlled restart.",
      evidence:["буфер сокращается", "несколько открытых actions", "давление на output растёт"],
      delayImpact:{line:-15, load:12, quality:-5}, delayText:"Остановка стала длиннее, backlog и давление на команду выросли.",
      actions:[
        A("Собрать cross-functional response: containment, owner, evidence, restart criteria", true, {line:16, quality:8, supplier:4, load:-4}, "Команда перешла от параллельного firefighting к общему recovery plan.", "restartControlled"),
        A("Запустить линию на пониженном темпе без закрытия рисков", false, {line:-10, quality:-14, load:5}, "Риск вернулся в поток вместе с незакрытыми причинами.", null),
        A("Передать все решения следующей смене", false, {line:-12, load:10, supplier:-4}, "Проблемы перешли в handover без containment.", null)
      ],
      messages:[
        M(2, "现在先统一风险清单、负责人、证据和恢复生产条件。", "Xiànzài xiān tǒngyī fēngxiǎn qīngdān, fùzérén, zhèngjù hé huīfù shēngchǎn tiáojiàn.", "First align the risk list, owners, evidence, and restart criteria.", "Сначала согласуйте список рисков, владельцев, evidence и критерии restart.", "Фраза задаёт единый recovery cadence."),
        M(1, "大家一起解决。", "Dàjiā yìqǐ jiějué.", "Let everyone solve it together.", "Давайте решать вместе.", "Командный посыл есть, но нет структуры."),
        M(0, "先开线再说。", "Xiān kāixiàn zài shuō.", "Restart the line first; we will discuss later.", "Сначала запустим линию, потом разберёмся.", "Output поставлен выше controlled restart.")
      ]
    },
    sequencing: {
      id:"sequencing", area:"Логистика / планирование", title:"Нужно защитить модельный микс", priority:4,
      summary:"Материала достаточно не на все варианты. Можно изменить последовательность, чтобы выиграть время до поставки.",
      evidence:["часть моделей имеет запас", "critical variant ограничен", "ETA в пределах смены"],
      delayImpact:{material:-10, line:-6}, delayText:"Без sequencing доступный запас продолжил расходоваться неэффективно.",
      actions:[
        A("Согласовать временный sequence по approved stock и точному ETA", true, {material:15, line:10, load:4}, "Модельный микс превратился в инструмент recovery.", "sequenceProtected"),
        A("Менять sequence без уведомления качества/планирования", false, {line:-5, quality:-6, load:7}, "Recovery создал новый coordination risk.", null),
        A("Не менять ничего, чтобы не усложнять план", false, {material:-16, line:-8}, "Производственная гибкость не использована.", null)
      ],
      messages:[
        M(2, "请按已批准库存和到货时间临时调整车型顺序，并同步质量和计划。", "Qǐng àn yǐ pīzhǔn kùcún hé dàohuò shíjiān línshí tiáozhěng chēxíng shùnxù, bìng tóngbù zhìliàng hé jìhuà.", "Temporarily adjust the model sequence based on approved stock and ETA, and align Quality and Planning.", "Временно измените sequence по утверждённому запасу и ETA, синхронизировав Quality и Planning.", "Формулировка учитывает cross-functional control."),
        M(1, "先换一下车型顺序。", "Xiān huàn yíxià chēxíng shùnxù.", "Change the model sequence for now.", "Пока поменяйте последовательность моделей.", "Не указаны основания и функции для синхронизации."),
        M(0, "随便排，只要不停线。", "Suíbiàn pái, zhǐyào bù tíngxiàn.", "Sequence it however you like as long as the line does not stop.", "Ставьте как угодно, лишь бы линия не остановилась.", "Неуправляемый sequencing создаёт новые риски.")
      ]
    },
    china_escalation: {
      id:"china_escalation", area:"Китай / поставщик", title:"Эскалация поставщику требует owner и deadline", priority:5,
      summary:"Несколько сообщений от поставщика содержат обещания, но нет одного владельца и подтверждённого control point.",
      evidence:["ETA менялся дважды", "owner не назван", "evidence частично"],
      delayImpact:{supplier:-14, material:-6, load:7}, delayText:"Без owner/deadline эскалация снова потеряла один control point.",
      actions:[
        A("Зафиксировать supplier owner, containment deadline, ETA checkpoint и evidence", true, {supplier:18, material:6, load:-2}, "Эскалация стала измеримой и управляемой.", "supplierOwner"),
        A("Добавить больше участников в чат без распределения ответственности", false, {supplier:-8, load:10}, "Количество участников выросло, owner так и не появился.", null),
        A("Попросить руководство поставщика 'ускориться' без конкретных данных", false, {supplier:-10, material:-4}, "Эскалация стала выше по уровню, но не точнее.", null)
      ],
      messages:[
        M(2, "请确认唯一负责人、临时措施完成时间、下一次ETA确认点和验证资料。", "Qǐng quèrèn wéiyī fùzérén, línshí cuòshī wánchéng shíjiān, xià yí cì ETA quèrèn diǎn hé yànzhèng zīliào.", "Confirm one accountable owner, containment completion time, the next ETA checkpoint, and verification evidence.", "Подтвердите одного ответственного owner, срок containment, следующий ETA checkpoint и evidence.", "Фраза делает escalation measurable."),
        M(1, "请尽快给我们答复。", "Qǐng jǐnkuài gěi wǒmen dáfù.", "Please reply as soon as possible.", "Ответьте как можно скорее.", "Нет deadline, owner и конкретных данных."),
        M(0, "我们领导很不满意。", "Wǒmen lǐngdǎo hěn bù mǎnyì.", "Our management is very unhappy.", "Наше руководство очень недовольно.", "Эмоциональная эскалация не заменяет operational control.")
      ]
    },
    first_off: {
      id:"first_off", area:"Качество / производство", title:"First-off перед восстановлением такта", priority:4,
      summary:"Коррекция процесса выполнена. Давление на выпуск растёт, но quality gate ещё не подтверждён.",
      evidence:["коррекция внесена", "первый автомобиль готов", "усиленный контроль не назначен"],
      delayImpact:{line:-4, load:5}, delayText:"Без решения restart задерживается, команда работает в неопределённости.",
      actions:[
        A("Проверить first-off, назначить enhanced control и только затем восстановить takt", true, {line:12, quality:14, load:-2}, "Restart получил evidence и контроль повторения.", "firstOffVerified"),
        A("Запустить takt сразу, first-off проверить позже", false, {quality:-16, line:-6}, "Объём вытеснил quality gate.", null),
        A("Оставить линию стоять до конца смены несмотря на успешную коррекцию", false, {line:-12, load:8}, "Evidence не превращено в controlled restart.", null)
      ],
      messages:[
        M(2, "首件确认合格并安排加强检查后，再恢复正常节拍。", "Shǒujiàn quèrèn hégé bìng ānpái jiāqiáng jiǎnchá hòu, zài huīfù zhèngcháng jiépāi.", "Resume normal takt only after the first-off is confirmed OK and enhanced checks are assigned.", "Возобновляйте нормальный takt только после подтверждения first-off и назначения усиленного контроля.", "Фраза чётко задаёт restart gate."),
        M(1, "首件没问题就开线。", "Shǒujiàn méi wèntí jiù kāixiàn.", "If the first-off is fine, restart the line.", "Если first-off нормальный, запускаем линию.", "Нет enhanced control и owner."),
        M(0, "赶产量，先开线。", "Gǎn chǎnliàng, xiān kāixiàn.", "We need output; restart first.", "Нужно догонять объём, сначала запускаем.", "Производительность поставлена выше quality evidence.")
      ]
    },
    handover: {
      id:"handover", area:"Смена / руководство", title:"Конец смены: передача открытых рисков", priority:5,
      summary:"До конца смены 25 минут. Есть закрытые actions, несколько наблюдений и минимум один риск, который может перейти следующей команде.",
      evidence:["часть actions закрыта", "несколько control points завтра", "следующая смена уже собирается"],
      delayImpact:{load:8, line:-4}, delayText:"Неполный handover переносит неопределённость в следующую смену.",
      actions:[
        A("Передать status по risk/owner/deadline/evidence/next checkpoint и unresolved items", true, {line:8, quality:8, material:6, supplier:6, load:-12}, "Следующая смена получает управляемую картину, а не набор сообщений.", "handoverControlled"),
        A("Передать только список 'что случилось' без owner и сроков", false, {load:8, supplier:-4, line:-3}, "Следующей смене придётся заново восстанавливать контекст.", null),
        A("Считать смену завершённой, если линия сейчас работает", false, {quality:-8, material:-6, supplier:-7}, "Текущая стабильность скрывает незакрытые control points.", null)
      ],
      messages:[
        M(2, "交接时请明确风险、负责人、截止时间、证据和下一检查点。", "Jiāojiē shí qǐng míngquè fēngxiǎn, fùzérén, jiézhǐ shíjiān, zhèngjù hé xià yí ge jiǎnchá diǎn.", "At handover, clearly state each risk, owner, deadline, evidence, and next checkpoint.", "При передаче смены чётко укажите риск, owner, deadline, evidence и следующий checkpoint.", "Это полноценная структура shift handover."),
        M(1, "这些问题下一班继续跟进。", "Zhèxiē wèntí xià yì bān jìxù gēnjìn.", "The next shift should continue following these issues.", "Следующая смена продолжит отслеживать эти вопросы.", "Нет конкретных владельцев и сроков."),
        M(0, "现在没停线，应该没事。", "Xiànzài méi tíngxiàn, yīnggāi méi shì.", "The line is running now, so it should be fine.", "Сейчас линия работает, значит, вероятно, всё нормально.", "Наличие output не означает отсутствие residual risk.")
      ]
    }
  });

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }
  function clamp(value) { return Math.max(0, Math.min(100, Number(value || 0))); }

  function snapshotLanguage() {
    return String(current().language || "chinese") === "english" ? "english" : "chinese";
  }

  function newRun() {
    return {
      turn:0,
      phase:"priority",
      language:snapshotLanguage(),
      metrics:{line:76, quality:72, material:70, supplier:54, load:28},
      flags:Object.create(null),
      selected:null,
      action:null,
      message:null,
      queue:[],
      history:[],
      priorityPoints:0,
      actionPoints:0,
      languagePoints:0,
      languageMax:0,
      handled:0,
      languageErrors:[],
      outcomeText:"Смена началась: производство стабильно, но несколько сигналов требуют внимания."
    };
  }

  function adjust(key, delta) {
    if (!run || !Object.prototype.hasOwnProperty.call(run.metrics, key)) return;
    run.metrics[key] = clamp(run.metrics[key] + Number(delta || 0));
  }

  function applyImpact(impact) {
    Object.keys(impact || {}).forEach(function (key) { adjust(key, impact[key]); });
  }

  function severityClass(value) {
    return value >= 5 ? "critical" : value >= 4 ? "high" : "watch";
  }

  function unique(ids) {
    const seen = Object.create(null);
    return ids.filter(function (id) {
      if (!INCIDENTS[id] || seen[id]) return false;
      seen[id] = true;
      return true;
    });
  }

  function queueForTurn() {
    if (!run) return [];
    if (run.turn === 0) return ["paint_repeat", "supplier_delay", "torque_alarm"];
    if (run.turn === 1) {
      return unique([
        run.flags.paintContained ? "weld_drift" : "paint_spread",
        run.flags.supplierExpedite ? "supplier_traceability" : "material_runout",
        run.flags.torqueProtected ? "first_off" : "quality_gate_hold"
      ]);
    }
    if (run.turn === 2) {
      return unique([
        run.metrics.material < 58 || run.flags.unapprovedSubstitution ? "engineering_substitution" : "sequencing",
        run.metrics.quality < 62 ? "quality_gate_hold" : "first_off",
        run.metrics.supplier < 62 ? "china_escalation" : "supplier_traceability"
      ]);
    }
    if (run.turn === 3) {
      return unique([
        run.metrics.line < 65 || run.metrics.load > 62 ? "line_stop" : "first_off",
        run.metrics.material < 60 ? "material_runout" : "sequencing",
        run.metrics.supplier < 72 ? "china_escalation" : "supplier_traceability"
      ]);
    }
    return unique([
      "handover",
      run.metrics.quality < 72 ? "quality_gate_hold" : "first_off",
      run.metrics.material < 68 ? "material_runout" : (run.metrics.supplier < 75 ? "china_escalation" : "sequencing")
    ]);
  }

  function ensureQueue() {
    if (!run || run.queue.length) return;
    run.queue = queueForTurn();
  }

  function metricMarkup() {
    return METRICS.map(function (metric) {
      const value = run.metrics[metric.key];
      const risk = metric.bad === "high" ? value >= 65 : value <= 45;
      const watch = metric.bad === "high" ? value >= 45 : value <= 65;
      const cls = risk ? "risk" : watch ? "watch" : "good";
      return '<div class="v624-metric ' + cls + '"><span>' + esc(metric.label) + '</span><b>' + value + '<small>/100</small></b>' +
        '<i><em style="width:' + value + '%"></em></i></div>';
    }).join("");
  }

  function headerMarkup() {
    const times = ["08:00", "09:35", "11:20", "14:05", "16:25"];
    return '<div class="v624-sim-head"><div><span>SHIFT SIMULATION · v6.0.24</span><h2>Виртуальная производственная смена</h2>' +
      '<p>Выберите, что разбирать первым, примите техническое решение и сформулируйте рабочее сообщение.</p></div>' +
      '<div class="v624-clock"><b>' + times[Math.min(run.turn, times.length - 1)] + '</b><small>Эпизод ' + (run.turn + 1) + ' / 5</small></div></div>' +
      '<div class="v624-metrics">' + metricMarkup() + '</div>';
  }

  function incidentCard(id) {
    const item = INCIDENTS[id];
    return '<button type="button" class="v624-incident-card ' + severityClass(item.priority) + '" data-v624-priority="' + esc(id) + '">' +
      '<div><span>' + esc(item.area) + '</span><b>P' + item.priority + '</b></div><h3>' + esc(item.title) + '</h3><p>' + esc(item.summary) + '</p>' +
      '<small>Сначала оцените риск для клиента, линии и времени до необратимого последствия.</small></button>';
  }

  function priorityMarkup() {
    ensureQueue();
    return headerMarkup() +
      '<section class="v624-stage"><div class="v624-stage-title"><span>01 · ПРИОРИТЕТ</span><h3>Одновременно пришло несколько сигналов. Что берёте первым?</h3>' +
      '<p>Невыбранные проблемы не исчезнут: до следующего эпизода они получат delay consequence.</p></div>' +
      '<div class="v624-incident-grid">' + run.queue.map(incidentCard).join("") + '</div></section>';
  }

  function evidenceMarkup(item) {
    return '<div class="v624-evidence"><span>Доступные факты</span>' +
      item.evidence.map(function (fact) { return '<b>' + esc(fact) + '</b>'; }).join("") + '</div>';
  }

  function actionMarkup() {
    const item = INCIDENTS[run.selected];
    return headerMarkup() +
      '<section class="v624-stage"><button type="button" class="v624-back" data-v624-back>← Вернуться к приоритетам</button>' +
      '<div class="v624-focus"><span>' + esc(item.area) + '</span><h3>' + esc(item.title) + '</h3><p>' + esc(item.summary) + '</p></div>' +
      evidenceMarkup(item) +
      '<div class="v624-stage-title"><span>02 · РЕШЕНИЕ</span><h3>Какое действие вы принимаете?</h3></div>' +
      '<div class="v624-action-list">' + item.actions.map(function (action, index) {
        return '<button type="button" data-v624-action="' + index + '"><b>' + String.fromCharCode(65 + index) + '</b><span>' + esc(action.label) + '</span></button>';
      }).join("") + '</div></section>';
  }

  function messageOptionMarkup(message, index) {
    if (run.language === "chinese") {
      return '<button type="button" data-v624-message="' + index + '"><b>' + String.fromCharCode(65 + index) + '</b><span class="v624-msg">' +
        '<strong>' + esc(message.zh) + '</strong><i>' + esc(message.pinyin) + '</i><small>' + esc(message.ru) + '</small></span></button>';
    }
    return '<button type="button" data-v624-message="' + index + '"><b>' + String.fromCharCode(65 + index) + '</b><span class="v624-msg">' +
      '<strong>' + esc(message.en) + '</strong><small>' + esc(message.ru) + '</small></span></button>';
  }

  function messageMarkup() {
    const item = INCIDENTS[run.selected];
    return headerMarkup() +
      '<section class="v624-stage"><div class="v624-focus compact"><span>' + esc(item.area) + '</span><h3>' + esc(item.title) + '</h3>' +
      '<p class="' + (run.action.correct ? "v624-good-text" : "v624-risk-text") + '">' + esc(run.action.outcome) + '</p></div>' +
      '<div class="v624-stage-title"><span>03 · КОММУНИКАЦИЯ</span><h3>Как сформулировать рабочее сообщение?</h3>' +
      '<p>' + (run.language === "chinese" ? "Выберите профессиональную реплику на путунхуа. Pinyin и русский смысл показаны для обучения." : "Выберите профессиональную shop-floor формулировку на английском.") + '</p></div>' +
      '<div class="v624-message-list">' + item.messages.map(messageOptionMarkup).join("") + '</div></section>';
  }

  function applyMessageEffect(item, message) {
    const delta = message.score === 2 ? 6 : message.score === 1 ? 1 : -6;
    if (item.area.indexOf("Китай") >= 0 || item.area.indexOf("постав") >= 0 || item.id.indexOf("supplier") >= 0 || item.id === "china_escalation") {
      adjust("supplier", delta);
      if (message.score === 2) adjust("material", 2);
    } else if (item.area.indexOf("Качество") >= 0 || item.area.indexOf("Окраска") >= 0 || item.area.indexOf("Сварка") >= 0) {
      adjust("quality", delta);
    } else {
      adjust("line", delta);
    }
    adjust("load", message.score === 2 ? -2 : message.score === 0 ? 4 : 1);
  }

  function ignoredConsequences(selectedId) {
    run.queue.forEach(function (id) {
      if (id === selectedId) return;
      const item = INCIDENTS[id];
      applyImpact(item.delayImpact);
      run.history.push({type:"delay", title:item.title, text:item.delayText, turn:run.turn});
    });
  }

  function feedbackMarkup() {
    const item = INCIDENTS[run.selected];
    const msg = run.message;
    const actionGood = run.action.correct;
    const languageGood = msg.score === 2;
    return headerMarkup() +
      '<section class="v624-stage"><div class="v624-result ' + (actionGood ? "good" : "risk") + '"><span>РЕЗУЛЬТАТ РЕШЕНИЯ</span><h3>' +
      (actionGood ? "Процесс защищён лучше" : "Риск увеличился") + '</h3><p>' + esc(run.action.outcome) + '</p></div>' +
      '<div class="v624-language-result ' + (languageGood ? "good" : msg.score === 1 ? "watch" : "risk") + '"><span>РАБОЧАЯ КОММУНИКАЦИЯ</span><b>' +
      (languageGood ? "Профессиональная формулировка" : msg.score === 1 ? "Понятно, но недостаточно конкретно" : "Формулировка усиливает риск") +
      '</b><p>' + esc(msg.feedback) + '</p></div>' +
      '<div class="v624-shift-note"><span>Что произошло с остальными сигналами</span><p>Пока вы занимались приоритетной проблемой, невыбранные события продолжили развиваться. Их delay-impact уже учтён в Live Shift State.</p></div>' +
      '<button type="button" class="primary v624-continue" data-v624-continue>' + (run.turn >= 4 ? "Завершить смену →" : "Продолжить смену →") + '</button></section>';
  }

  function weakestMetric() {
    const normalized = {
      line:run.metrics.line,
      quality:run.metrics.quality,
      material:run.metrics.material,
      supplier:run.metrics.supplier,
      load:100 - run.metrics.load
    };
    return Object.keys(normalized).sort(function (a, b) { return normalized[a] - normalized[b]; })[0];
  }

  function scorecard() {
    const process = Math.round((run.metrics.line + run.metrics.quality + run.metrics.material + run.metrics.supplier + (100 - run.metrics.load)) / 5);
    const priority = Math.round((run.priorityPoints / Math.max(1, run.handled)) * 100);
    const judgement = Math.round((run.actionPoints / Math.max(1, run.handled)) * 100);
    const language = Math.round((run.languagePoints / Math.max(1, run.languageMax)) * 100);
    const total = Math.round(process * 0.4 + priority * 0.2 + judgement * 0.25 + language * 0.15);
    return {process:process, priority:priority, judgement:judgement, language:language, total:total};
  }

  function recommendation() {
    const weakest = weakestMetric();
    const map = {
      line:"Сильнее фиксируйте restart criteria, owners и порядок реакции на Andon/line stop.",
      quality:"Раньше замораживайте suspect window и требуйте traceability/evidence до release.",
      material:"Считайте run-out и используйте sequencing, approved stock и подтверждённый ETA как единый recovery plan.",
      supplier:"Делайте запросы измеримыми: part/lot/quantity + owner + deadline + evidence.",
      load:"Снижайте параллельный firefighting: один owner, один checkpoint и короткий cross-functional cadence."
    };
    return map[weakest];
  }

  function summaryMarkup() {
    const score = scorecard();
    const title = score.total >= 85 ? "Смена под контролем" : score.total >= 70 ? "Стабильная смена" : score.total >= 55 ? "Смена удержана с рисками" : "Риски накопились";
    const errors = run.languageErrors.slice(0, 3);
    return '<div class="v624-summary"><div class="v624-summary-head"><span>SHIFT REVIEW · v6.0.24</span><h2>' + esc(title) + '</h2>' +
      '<p>Итог учитывает состояние производства, порядок приоритетов, технические решения и качество рабочей коммуникации.</p></div>' +
      '<div class="v624-total"><b>' + score.total + '<small>/100</small></b><span>Общий результат смены</span></div>' +
      '<div class="v624-score-grid">' +
        '<div><span>Production control</span><b>' + score.process + '</b></div>' +
        '<div><span>Prioritization</span><b>' + score.priority + '</b></div>' +
        '<div><span>Production judgement</span><b>' + score.judgement + '</b></div>' +
        '<div><span>Language</span><b>' + score.language + '</b></div>' +
      '</div>' +
      '<div class="v624-review-grid"><section><span>Главная точка роста</span><p>' + esc(recommendation()) + '</p></section>' +
      '<section><span>Live Shift State к концу</span><div class="v624-final-metrics">' + METRICS.map(function (metric) {
        return '<b>' + esc(metric.label) + '<small>' + run.metrics[metric.key] + '/100</small></b>';
      }).join("") + '</div></section></div>' +
      '<section class="v624-language-review"><span>Языковой разбор</span>' +
        (errors.length ? errors.map(function (error) {
          return '<div><b>' + esc(error.context) + '</b><p>' + esc(error.feedback) + '</p><small>Лучше: ' + esc(error.better) + '</small></div>';
        }).join("") : '<p>Во всех эпизодах выбраны профессиональные рабочие формулировки.</p>') +
      '</section>' +
      '<div class="v624-summary-actions"><button type="button" class="primary" data-v624-restart>Повторить смену</button>' +
      '<button type="button" data-v624-close>Вернуться к 20 играм</button></div>' +
      '<small class="v624-no-xp">Shift Simulation — обучающий режим. Он не начисляет отдельный XP и не меняет backend-лимит пяти ответов.</small></div>';
  }

  function shellMarkup() {
    if (!run) return "";
    if (run.phase === "priority") return '<section class="v624-sim-shell">' + priorityMarkup() + '</section>';
    if (run.phase === "action") return '<section class="v624-sim-shell">' + actionMarkup() + '</section>';
    if (run.phase === "message") return '<section class="v624-sim-shell">' + messageMarkup() + '</section>';
    if (run.phase === "feedback") return '<section class="v624-sim-shell">' + feedbackMarkup() + '</section>';
    return '<section class="v624-sim-shell complete">' + summaryMarkup() + '</section>';
  }

  function renderSimulator() {
    const host = query(".v624-sim-host");
    if (!host || !run) return false;
    host.innerHTML = shellMarkup();
    bindSimulator(host);
    return true;
  }

  function bestPriority(queue) {
    return Math.max.apply(null, queue.map(function (id) { return INCIDENTS[id].priority; }));
  }

  function bindSimulator(host) {
    queryAll("[data-v624-priority]", host).forEach(function (button) {
      button.addEventListener("click", function () {
        const id = button.dataset.v624Priority;
        if (!INCIDENTS[id]) return;
        const best = bestPriority(run.queue);
        if (INCIDENTS[id].priority === best) run.priorityPoints += 1;
        run.selected = id;
        run.phase = "action";
        renderSimulator();
      });
    });

    const back = query("[data-v624-back]", host);
    if (back) back.addEventListener("click", function () {
      run.selected = null;
      run.phase = "priority";
      renderSimulator();
    });

    queryAll("[data-v624-action]", host).forEach(function (button) {
      button.addEventListener("click", function () {
        const item = INCIDENTS[run.selected];
        const action = item.actions[Number(button.dataset.v624Action)];
        if (!action) return;
        run.action = action;
        applyImpact(action.impact);
        if (action.flag) run.flags[action.flag] = true;
        if (action.correct) run.actionPoints += 1;
        run.phase = "message";
        renderSimulator();
      });
    });

    queryAll("[data-v624-message]", host).forEach(function (button) {
      button.addEventListener("click", function () {
        const item = INCIDENTS[run.selected];
        const message = item.messages[Number(button.dataset.v624Message)];
        if (!message) return;
        run.message = message;
        run.languageMax += 2;
        run.languagePoints += message.score;
        applyMessageEffect(item, message);
        if (message.score < 2) {
          const best = item.messages.find(function (entry) { return entry.score === 2; });
          run.languageErrors.push({
            context:item.title,
            feedback:message.feedback,
            better:run.language === "chinese" ? best.zh + " — " + best.ru : best.en + " — " + best.ru
          });
        }
        ignoredConsequences(run.selected);
        run.handled += 1;
        run.history.push({type:"handled", title:item.title, text:run.action.outcome, turn:run.turn});
        run.phase = "feedback";
        renderSimulator();
      });
    });

    const next = query("[data-v624-continue]", host);
    if (next) next.addEventListener("click", function () {
      if (run.turn >= 4) {
        run.phase = "complete";
      } else {
        run.turn += 1;
        run.phase = "priority";
        run.queue = [];
        run.selected = null;
        run.action = null;
        run.message = null;
      }
      renderSimulator();
    });

    const restart = query("[data-v624-restart]", host);
    if (restart) restart.addEventListener("click", function () {
      run = newRun();
      renderSimulator();
    });

    const close = query("[data-v624-close]", host);
    if (close) close.addEventListener("click", function () {
      run = null;
      host.innerHTML = "";
      const launcher = query(".v624-launcher");
      if (launcher && launcher.scrollIntoView) launcher.scrollIntoView({behavior:"smooth", block:"center"});
    });
  }

  function decorateCatalog() {
    const host = query(".v623-catalog-panel") || query(".v622-catalog-panel") || query(".v621-difficulty-panel");
    if (!host) return false;
    if (!query(".v624-launcher")) {
      host.insertAdjacentHTML("afterend",
        '<section class="v624-launcher"><div><span>SHIFT SIMULATION · v6.0.24</span><h2>Проживите целую производственную смену</h2>' +
        '<p>Пять связанных эпизодов: вы выбираете приоритет, принимаете техническое решение и формулируете рабочее сообщение на китайском или английском. Невыбранные проблемы продолжают развиваться.</p></div>' +
        '<div class="v624-launcher-flow"><span>Приоритет</span><b>→</b><span>Решение</span><b>→</b><span>Коммуникация</span><b>→</b><span>Последствие</span><b>→</b><span>Shift Review</span></div>' +
        '<button type="button" class="primary" data-v624-start>Начать виртуальную смену</button></section>' +
        '<div class="v624-sim-host" aria-live="polite"></div>');
    }
    const start = query("[data-v624-start]");
    if (start && start.dataset.v624Bound !== "1") {
      start.dataset.v624Bound = "1";
      start.addEventListener("click", function () {
        run = newRun();
        renderSimulator();
        const sim = query(".v624-sim-host");
        if (sim && sim.scrollIntoView) sim.scrollIntoView({behavior:"smooth", block:"start"});
      });
    }
    return true;
  }

  function decorate() {
    scheduled = false;
    if (String(current().view || "") !== "games") {
      run = null;
      return;
    }
    decorateCatalog();
    if (run) {
      const host = query(".v624-sim-host");
      if (host && !query(".v624-sim-shell", host)) renderSimulator();
    }
  }

  function scheduleDecorate() {
    if (scheduled) return;
    scheduled = true;
    if (root.requestAnimationFrame) root.requestAnimationFrame(decorate);
    else root.setTimeout(decorate, 0);
  }

  function install() {
    if (installed) return;
    installed = true;
    const main = query("#main");
    if (main && root.MutationObserver) {
      observer = new MutationObserver(scheduleDecorate);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener("mgc:state-change", scheduleDecorate);
    document.addEventListener("mgc:frontend-ready", scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register("shift-simulation-v624", {
    metrics:METRICS,
    incidents:INCIDENTS,
    queueForTurn:queueForTurn,
    scorecard:scorecard,
    decorate:decorate,
    install:install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
