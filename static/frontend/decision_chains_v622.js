/* v6.0.22: multi-step automotive decisions with consequences and bilingual shop-floor language. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("decision-chains-v622")) return;

  const records = new Map();
  const CHAIN_STEPS = 3;
  let installed = false;
  let observer = null;
  let scheduled = false;

  function S(prompt, correctIndex, labels, consequences, zh, pinyin, en, ru) {
    return {
      prompt: prompt,
      options: labels.map(function (label, index) {
        return {label: label, correct: index === correctIndex, consequence: consequences[index]};
      }),
      phrase: {chinese: zh, pinyin: pinyin, english: en, russian: ru}
    };
  }

  const CHAINS = Object.freeze({
    line_stop: {
      title: "Andon / Line Stop",
      subtitle: "Stop risk → contain → verified restart",
      steps: [
        S(
          "На посту обнаружен риск качества, который может уйти на следующий автомобиль. Первое действие?", 1,
          ["Продолжить до конца такта и сообщить позже", "Активировать Andon и остановить рискованную операцию", "Сразу искать виновного оператора"],
          ["Подозрительные автомобили продолжают двигаться по потоку, зона риска растёт.", "Риск локализован в точке возникновения, команда получает время на проверку.", "Время уходит на персонализацию проблемы, а процесс остаётся неконтролируемым."],
          "请先停止有风险的工序并启动安灯。", "Qǐng xiān tíngzhǐ yǒu fēngxiǎn de gōngxù bìng qǐdòng āndēng.",
          "Please stop the risky operation first and activate the Andon.", "Сначала остановите рискованную операцию и активируйте Andon."
        ),
        S(
          "Линия остановлена. Что нужно сделать до попытки перезапуска?", 0,
          ["Проверить last known good, изолировать подозрительное и назначить владельца", "Перезапустить, если визуально всё выглядит нормально", "Ждать письменного отчёта конца смены"],
          ["Граница дефекта и ответственность определены, дальнейшее решение опирается на факты.", "Без подтверждённой границы дефекта возможен повторный выпуск несоответствия.", "Оперативное containment не выполнено, остановка становится неуправляемой."],
          "请确认最后一个合格件，并隔离所有可疑件。", "Qǐng quèrèn zuìhòu yí ge hégé jiàn, bìng gélí suǒyǒu kěyí jiàn.",
          "Confirm the last known good part and segregate all suspect parts.", "Подтвердите последнюю годную деталь и изолируйте все подозрительные."
        ),
        S(
          "Какое условие достаточно для управляемого перезапуска?", 2,
          ["Мастер считает, что проблема больше не повторится", "Нужно наверстать план, поэтому запускаем без first-off", "Исправление подтверждено, first-off проверен, владелец и контроль определены"],
          ["Мнение без доказательства не закрывает риск повторного дефекта.", "Объём вытесняет quality gate и повышает риск повторной остановки.", "Перезапуск имеет проверяемое основание и усиленный контроль."],
          "首件确认合格后才能恢复生产。", "Shǒujiàn quèrèn hégé hòu cái néng huīfù shēngchǎn.",
          "Production may resume only after the first-off part is confirmed OK.", "Производство можно возобновить только после подтверждения first-off."
        )
      ]
    },
    quality: {
      title: "Quality Escalation",
      subtitle: "Containment → traceability → root cause/action",
      steps: [
        S(
          "На автомобиле найден повторяющийся дефект. Что важнее сделать первым?", 0,
          ["Изолировать затронутые и потенциально затронутые единицы", "Сразу потребовать финальный 8D", "Снизить критерий приемки на смену"],
          ["Containment предотвращает дальнейшее распространение несоответствия.", "Root cause важен, но без containment дефект продолжает уходить дальше.", "Изменение критерия без инженерного основания маскирует проблему."],
          "请立即隔离受影响和可疑的车辆。", "Qǐng lìjí gélí shòu yǐngxiǎng hé kěyí de chēliàng.",
          "Immediately contain the affected and potentially affected vehicles.", "Немедленно изолируйте затронутые и потенциально затронутые автомобили."
        ),
        S(
          "Containment выполнен. Как определить реальный масштаб проблемы?", 1,
          ["Проверить только один следующий автомобиль", "Проверить traceability, время, партию и last known good", "Считать затронутой только первую найденную единицу"],
          ["Один образец не подтверждает границу партии или временного окна.", "Граница риска строится по прослеживаемости, а не по предположению.", "Повторяемый дефект может уже находиться в незавершённом производстве."],
          "请确认追溯信息、批次和最后一个合格件。", "Qǐng quèrèn zhuīsù xìnxī, pīcì hé zuìhòu yí ge hégé jiàn.",
          "Confirm traceability, the batch, and the last known good unit.", "Подтвердите прослеживаемость, партию и последнюю заведомо годную единицу."
        ),
        S(
          "Масштаб подтверждён. Что закрывает проблему на уровне процесса?", 2,
          ["Только сортировка всей партии", "Устное обещание не допустить повторения", "Root cause + corrective action + effectiveness check + owner"],
          ["Сортировка защищает клиента, но не устраняет причину повторения.", "Без причины, действия и проверки эффективности риск остаётся неконтролируемым.", "Проблема получает техническое закрытие и контроль эффективности."],
          "请提供根本原因、纠正措施和效果验证。", "Qǐng tígōng gēnběn yuányīn, jiūzhèng cuòshī hé xiàoguǒ yànzhèng.",
          "Provide the root cause, corrective action, and effectiveness verification.", "Предоставьте корневую причину, корректирующее действие и проверку эффективности."
        )
      ]
    },
    logistics: {
      title: "Material Shortage",
      subtitle: "Run-out → recovery route → ETA/owner",
      steps: [
        S(
          "Поставщик сообщает о задержке критичного компонента. Что проверить сначала?", 2,
          ["Сразу остановить всю сборку", "Ждать плановую поставку без пересчёта", "Фактический остаток, расход, run-out и затронутые модели"],
          ["Без расчёта run-out можно создать ненужную потерю производства.", "Скрытый дефицит проявится слишком поздно для управляемого восстановления.", "Команда понимает реальное окно до дефицита и может приоритизировать действия."],
          "请确认库存、消耗速度和预计断料时间。", "Qǐng quèrèn kùcún, xiāohào sùdù hé yùjì duànliào shíjiān.",
          "Confirm stock, consumption rate, and the estimated run-out time.", "Подтвердите запас, скорость расхода и ожидаемое время исчерпания."
        ),
        S(
          "Run-out подтверждён. Как строить recovery plan?", 1,
          ["Отправить поставщику только сообщение «срочно»", "Проверить expedite, альтернативный маршрут, approved stock и приоритет моделей", "Самостоятельно заменить компонент на похожий"],
          ["Без количества, маршрута и времени запрос не превращается в исполнимый план.", "Recovery plan использует несколько управляемых рычагов и защищает линию.", "Неутверждённая замена создаёт риск BOM, качества и сертификации."],
          "请确认加急方案、替代运输路线和可用合格库存。", "Qǐng quèrèn jiājí fāng'àn, tìdài yùnshū lùxiàn hé kěyòng hégé kùcún.",
          "Confirm the expedite plan, alternative transport route, and available approved stock.", "Подтвердите expedite-план, альтернативный маршрут и доступный утверждённый запас."
        ),
        S(
          "Recovery plan согласован. Что должно остаться в управлении смены?", 0,
          ["Подтверждённый ETA, количество, владелец, control point и fallback", "Только номер машины перевозчика", "Фраза «поставка в пути»"],
          ["План становится измеримым, а отклонение видно до фактического line stop.", "Номер транспорта не даёт управляемого ETA и ответственности.", "Статус без времени, количества и владельца не защищает производство."],
          "请确认到达时间、数量、负责人和下一检查点。", "Qǐng quèrèn dàodá shíjiān, shùliàng, fùzérén hé xià yí ge jiǎnchá diǎn.",
          "Confirm ETA, quantity, owner, and the next control point.", "Подтвердите ETA, количество, владельца и следующую контрольную точку."
        )
      ]
    },
    welding: {
      title: "Body Shop Containment",
      subtitle: "Suspect body → parameters/fixture → verified restart",
      steps: [
        S(
          "На кузове обнаружен нестабильный сварной контакт. Первое решение?", 1,
          ["Добавить ещё одну точку вручную без оценки", "Изолировать кузова с last known good и остановить рискованную операцию", "Отправить кузов дальше на финальный контроль"],
          ["Несогласованное изменение процесса не доказывает соответствие конструкции.", "Подозрительный диапазон удерживается до подтверждения качества.", "Дефект уходит downstream, стоимость исправления и объём риска растут."],
          "请隔离可疑车身并停止有风险的焊接工序。", "Qǐng gélí kěyí chēshēn bìng tíngzhǐ yǒu fēngxiǎn de hànjiē gōngxù.",
          "Contain the suspect bodies and stop the risky welding operation.", "Изолируйте подозрительные кузова и остановите рискованную сварочную операцию."
        ),
        S(
          "Что проверять для локализации причины в сварочном процессе?", 2,
          ["Только внешний вид одной точки", "Только скорость конвейера", "Ток/время/усилие, электроды, позиционирование и fixture"],
          ["Визуальный признак не подтверждает стабильность параметров соединения.", "Скорость не заменяет проверку сварочных параметров и оснастки.", "Проверяются параметры процесса и геометрические причины нестабильности."],
          "请检查焊接参数、电极状态和夹具定位。", "Qǐng jiǎnchá hànjiē cānshù, diànjí zhuàngtài hé jiājù dìngwèi.",
          "Check the welding parameters, electrode condition, and fixture location.", "Проверьте параметры сварки, состояние электродов и позиционирование оснастки."
        ),
        S(
          "После корректировки процесса что требуется перед серийным продолжением?", 0,
          ["Проверенный repair/first-off и подтверждение параметров контроля", "Только сброс alarm робота", "Увеличить темп для компенсации остановки"],
          ["Перезапуск подтверждён фактическим результатом и стабильными параметрами.", "Сброс alarm не подтверждает качество соединения.", "Повышение темпа сразу после нестабильности увеличивает риск повторения."],
          "首件和焊接参数确认合格后再继续生产。", "Shǒujiàn hé hànjiē cānshù quèrèn hégé hòu zài jìxù shēngchǎn.",
          "Continue production only after the first-off and welding parameters are confirmed OK.", "Продолжайте производство только после подтверждения first-off и параметров сварки."
        )
      ]
    },
    paint: {
      title: "Paint Process Recovery",
      subtitle: "Hold → process check → first-off confirmation",
      steps: [
        S(
          "На нескольких кузовах появился повторяющийся дефект покрытия. Что делать первым?", 0,
          ["Удержать затронутые кузова и определить границу дефекта", "Полировать все кузова без классификации", "Продолжить до конца партии"],
          ["Дефект не уходит дальше, а зона риска становится измеримой.", "Rework до понимания дефекта может скрыть симптом и потерять данные.", "Повторяемый дефект размножается на дополнительные автомобили."],
          "请先扣留受影响的车身并确认问题范围。", "Qǐng xiān kòuliú shòu yǐngxiǎng de chēshēn bìng quèrèn wèntí fànwéi.",
          "Hold the affected bodies first and confirm the scope of the issue.", "Сначала удержите затронутые кузова и подтвердите масштаб проблемы."
        ),
        S(
          "Какая проверка процесса наиболее полезна при повторяемом дефекте окраски?", 2,
          ["Только цвет кузова", "Только фамилия оператора предыдущей смены", "Материал/вязкость, spray parameters, робот, температура/влажность и booth"],
          ["Цвет помогает сегментировать данные, но не заменяет проверку процесса.", "Персональная привязка не локализует техническую причину.", "Проверяются параметры, способные системно влиять на поверхность покрытия."],
          "请检查涂料黏度、喷涂参数和喷房环境。", "Qǐng jiǎnchá túliào niándù, pēntú cānshù hé pēnfáng huánjìng.",
          "Check paint viscosity, spray parameters, and booth conditions.", "Проверьте вязкость материала, параметры распыления и условия камеры."
        ),
        S(
          "Коррекция внесена. Что подтверждает безопасное возвращение процесса?", 1,
          ["Робот снова движется без alarm", "First-off прошёл surface check, rework определён, усиленный контроль назначен", "Камера прогрета до плановой температуры"],
          ["Работоспособность робота не подтверждает качество покрытия.", "Исправление подтверждено на продукте, раннее повторение будет обнаружено.", "Один параметр не доказывает восстановление всей системы окраски."],
          "首件表面检查合格后再恢复正常节拍。", "Shǒujiàn biǎomiàn jiǎnchá hégé hòu zài huīfù zhèngcháng jiépāi.",
          "Return to normal takt only after the first-off surface check is OK.", "Возвращайтесь к нормальному такту только после успешной проверки first-off."
        )
      ]
    },
    safety: {
      title: "Safety Near Miss",
      subtitle: "Stop exposure → correct barrier → verified restart",
      steps: [
        S(
          "Погрузчик пересёк пешеходную зону рядом с работающим постом. Первое действие?", 2,
          ["Сделать фотографию и продолжить работу", "Предупредить только следующую смену", "Остановить опасное взаимодействие и исключить дальнейшее воздействие"],
          ["Фиксация полезна, но опасное состояние остаётся активным.", "Текущая смена продолжает работать с известным риском.", "Экспозиция риска прекращена до разбора причины."],
          "请立即停止危险作业并隔离风险区域。", "Qǐng lìjí tíngzhǐ wēixiǎn zuòyè bìng gélí fēngxiǎn qūyù.",
          "Stop the unsafe activity immediately and isolate the risk area.", "Немедленно остановите опасную работу и изолируйте зону риска."
        ),
        S(
          "Какое действие устраняет причину, а не только симптом?", 0,
          ["Восстановить разделение потоков, visibility/маркировку и правила движения", "Попросить всех быть внимательнее", "Перенести предупреждающий знак на соседнюю стену"],
          ["Изменение барьера и стандарта снижает вероятность повторения.", "Призыв к внимательности слабее инженерного или организационного барьера.", "Косметическое изменение не восстанавливает безопасную организацию потоков."],
          "请恢复人车分流并确认安全通道。", "Qǐng huīfù rén chē fēnliú bìng quèrèn ānquán tōngdào.",
          "Restore pedestrian-vehicle separation and confirm the safe route.", "Восстановите разделение пешеходного и транспортного потоков."
        ),
        S(
          "Когда участок можно вернуть в нормальную работу?", 1,
          ["Сразу после освобождения прохода", "После проверки барьеров, информирования команды и подтверждения safe state", "Когда закончится текущая смена"],
          ["Освобождение прохода не подтверждает восстановление системы предотвращения.", "Перезапуск основан на проверенном устранении риска.", "Время само по себе не устраняет опасное условие."],
          "确认防护措施有效后才能恢复作业。", "Quèrèn fánghù cuòshī yǒuxiào hòu cái néng huīfù zuòyè.",
          "Work may resume only after the protective measures are verified effective.", "Работу можно возобновить только после подтверждения эффективности защитных мер."
        )
      ]
    },
    engineering: {
      title: "Engineering Change",
      subtitle: "Scope → downstream impact → controlled release",
      steps: [
        S(
          "Поступило изменение компонента от поставщика. Что проверить первым?", 1,
          ["Сразу заменить номер в BOM", "Affected part/variant, reason, drawing/spec revision и effective point", "Передать письмо напрямую на линию"],
          ["Изменение BOM без revision/effective point создаёт конфигурационный риск.", "Инженер понимает объект изменения и границу его применения.", "Неуправляемая информация может попасть в производство до инженерного решения."],
          "请确认零件版本、变更原因和生效时间点。", "Qǐng quèrèn língjiàn bǎnběn, biàngēng yuányīn hé shēngxiào shíjiān diǎn.",
          "Confirm the part revision, change reason, and effective point.", "Подтвердите ревизию детали, причину изменения и точку применения."
        ),
        S(
          "Какие downstream-объекты нужно оценить до release?", 0,
          ["BOM, drawing/spec, WI, tooling, quality plan, stock и affected vehicles", "Только CAD-модель", "Только закупочную цену"],
          ["Изменение проверяется по всей цепочке цифрового и физического производства.", "CAD не отражает все документы, запасы и производственные зависимости.", "Стоимость важна, но не определяет техническую применимость изменения."],
          "请评估BOM、图纸、作业指导书和现有库存的影响。", "Qǐng pínggū BOM, túzhǐ, zuòyè zhǐdǎoshū hé xiànyǒu kùcún de yǐngxiǎng.",
          "Assess the impact on BOM, drawings, work instructions, and current stock.", "Оцените влияние на BOM, чертежи, рабочие инструкции и текущий запас."
        ),
        S(
          "Что делает engineering change управляемым при запуске?", 2,
          ["Устная договорённость инженера и мастера", "Удаление старой версии из общей папки", "Approved release, effective point, owner, old-stock disposition и first verification"],
          ["Без release и effective point функции могут использовать разные версии.", "Удаление файла не заменяет change record и disposition остатка.", "Конфигурация имеет однозначную границу и проверку первого применения."],
          "请确认批准版本、生效点和旧库存处理方案。", "Qǐng quèrèn pīzhǔn bǎnběn, shēngxiào diǎn hé jiù kùcún chǔlǐ fāng'àn.",
          "Confirm the approved revision, effective point, and old-stock disposition.", "Подтвердите утверждённую ревизию, точку применения и решение по старому запасу."
        )
      ]
    },
    supplier: {
      title: "Supplier Escalation",
      subtitle: "Facts → containment → owner/deadline/evidence",
      steps: [
        S(
          "Китайскому поставщику нужно сообщить о проблеме. Какая первая формулировка лучше?", 2,
          ["«У вас опять плохое качество»", "«Срочно разберитесь» без номера детали", "Факт дефекта + part/lot + количество + где обнаружено"],
          ["Общее обвинение не даёт данных для containment и анализа.", "Без идентификации поставщик не может локализовать продукт и партию.", "Поставщик получает проверяемую проблему, а не эмоциональную оценку."],
          "我们发现该批次零件存在重复缺陷，请确认批次和数量。", "Wǒmen fāxiàn gāi pīcì língjiàn cúnzài chóngfù quēxiàn, qǐng quèrèn pīcì hé shùliàng.",
          "We found a repeated defect in this lot. Please confirm the lot and quantity.", "Мы обнаружили повторяющийся дефект в этой партии. Подтвердите партию и количество."
        ),
        S(
          "Какой запрос защищает производство до готовности root cause?", 1,
          ["Только полный 8D через неделю", "Немедленный containment: stock check, segregation, certified/sorted shipment и ETA", "Скидка на следующую поставку"],
          ["Без временного containment завод остаётся под текущим риском.", "Производство получает защиту до завершения долгосрочного анализа.", "Коммерческая компенсация не защищает качество текущих деталей."],
          "请立即隔离库存，并提供筛选后合格批次的预计到达时间。", "Qǐng lìjí gélí kùcún, bìng tígōng shāixuǎn hòu hégé pīcì de yùjì dàodá shíjiān.",
          "Please contain the stock immediately and provide the ETA for a certified sorted lot.", "Немедленно изолируйте запас и сообщите ETA проверенной отсортированной партии."
        ),
        S(
          "Как завершить эскалацию так, чтобы она была управляемой?", 0,
          ["Owner + containment deadline + root-cause deadline + verification evidence", "«Ждём ответа как можно скорее»", "Создать большой чат без распределения ответственности"],
          ["Следующие шаги измеримы по владельцу, времени и evidence.", "Нет конкретного срока, владельца и критерия завершения.", "Количество участников не заменяет owner и decision cadence."],
          "请确认负责人、临时措施期限、根本原因期限和验证资料。", "Qǐng quèrèn fùzérén, línshí cuòshī qīxiàn, gēnběn yuányīn qīxiàn hé yànzhèng zīliào.",
          "Confirm the owner, containment deadline, root-cause deadline, and verification evidence.", "Подтвердите владельца, срок containment, срок root cause и доказательство проверки."
        )
      ]
    }
  });

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function depth() { return frontend.get("game-depth-v621"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }

  function familyFor(scene, gameType) {
    if (gameType === "dialogue_choice") return "supplier";
    if (scene === "paint") return "paint";
    if (scene === "welding") return "welding";
    if (scene === "logistics" || scene === "warehouse") return "logistics";
    if (scene === "safety") return "safety";
    if (scene === "engineering") return "engineering";
    if (scene === "meeting") return "supplier";
    if (scene === "quality" || scene === "body" || scene === "vehicle") return "quality";
    return "line_stop";
  }

  function shouldChain(level) {
    return level === "shift" || level === "expert";
  }

  function recordFor(key) {
    if (!records.has(key)) {
      records.set(key, {step: 0, selection: null, correct: 0, risks: [], choices: [], done: false});
      if (records.size > 100) records.delete(records.keys().next().value);
    }
    return records.get(key);
  }

  function phraseMarkup(step) {
    const language = String(current().language || "chinese");
    if (language === "chinese") {
      return '<div class="v622-language"><span>Рабочая фраза · 中文</span><b>' + esc(step.phrase.chinese) + '</b>' +
        '<i>' + esc(step.phrase.pinyin) + '</i><small>' + esc(step.phrase.russian) + '</small></div>';
    }
    return '<div class="v622-language"><span>Shop-floor English</span><b>' + esc(step.phrase.english) + '</b>' +
      '<small>' + esc(step.phrase.russian) + '</small></div>';
  }

  function lockStage(stage) {
    stage.classList.add("v622-chain-locked");
    queryAll('button,[role="button"],input,select', stage).forEach(function (node) {
      if (node.closest && node.closest(".v622-chain-panel")) return;
      if (node.dataset.v622Locked === "1") return;
      node.dataset.v622Locked = "1";
      if ("disabled" in node) {
        node.dataset.v622WasDisabled = node.disabled ? "1" : "0";
        node.disabled = true;
      }
      if (node.hasAttribute && node.hasAttribute("tabindex")) node.dataset.v622Tabindex = node.getAttribute("tabindex");
      if (node.setAttribute) {
        node.setAttribute("aria-disabled", "true");
        if (!("disabled" in node)) node.setAttribute("tabindex", "-1");
      }
    });
  }

  function unlockStage(stage) {
    stage.classList.remove("v622-chain-locked");
    queryAll('[data-v622-locked="1"]', stage).forEach(function (node) {
      if ("disabled" in node) node.disabled = node.dataset.v622WasDisabled === "1";
      if (node.removeAttribute) node.removeAttribute("aria-disabled");
      if (!("disabled" in node)) {
        if (node.dataset.v622Tabindex !== undefined) node.setAttribute("tabindex", node.dataset.v622Tabindex);
        else node.removeAttribute("tabindex");
      }
      delete node.dataset.v622Locked;
      delete node.dataset.v622WasDisabled;
      delete node.dataset.v622Tabindex;
    });
  }

  function stepPanel(chain, record, level) {
    const step = chain.steps[record.step];
    const selected = record.selection;
    return '<div class="v622-chain-head"><div><span>PRODUCTION DECISION CHAIN</span><h2>' + esc(chain.title) + '</h2><p>' + esc(chain.subtitle) + '</p></div>' +
      '<div class="v622-chain-meter"><b>' + (record.step + 1) + ' / ' + CHAIN_STEPS + '</b><small>' + (level === "expert" ? "EXPERT" : "SHIFT") + '</small></div></div>' +
      '<div class="v622-chain-track"><i class="done"></i><i class="' + (record.step >= 1 ? "done" : "") + '"></i><i class="' + (record.step >= 2 ? "done" : "") + '"></i></div>' +
      '<div class="v622-chain-question"><span>Шаг ' + (record.step + 1) + '</span><h3>' + esc(step.prompt) + '</h3></div>' +
      '<div class="v622-chain-options">' + step.options.map(function (option, index) {
        let cls = "";
        if (selected) cls = index === selected.index ? (selected.correct ? " selected correct" : " selected wrong") : " muted";
        return '<button type="button" data-v622-option="' + index + '" class="' + cls.trim() + '"' + (selected ? " disabled" : "") + '>' +
          '<b>' + String.fromCharCode(65 + index) + '</b><span>' + esc(option.label) + '</span></button>';
      }).join("") + '</div>' +
      (selected ? '<div class="v622-consequence ' + (selected.correct ? "good" : "risk") + '"><b>' +
        (selected.correct ? "Решение защищает процесс" : "Последствие неправильного решения") + '</b><p>' + esc(selected.consequence) + '</p></div>' +
        phraseMarkup(step) + '<div class="v622-chain-actions"><span>Production judgement: <b>' + record.correct + '/' + record.choices.length +
        '</b> · рисков: <b>' + record.risks.length + '</b></span><button type="button" class="primary" data-v622-next>' +
        (record.step === CHAIN_STEPS - 1 ? "Завершить цепочку" : "Следующий шаг →") + '</button></div>' : "") +
      '<small class="v622-no-xp">Decision Chain развивает производственное мышление и не создаёт отдельный XP-фарм.</small>';
  }

  function completePanel(chain, record, level) {
    const score = record.correct;
    const status = score === 3 ? "Стабильное решение" : score >= 2 ? "Рабочее решение" : "Нужно усилить приоритизацию";
    return '<div class="v622-complete"><span>DECISION CHAIN COMPLETE</span><h2>' + esc(status) + '</h2>' +
      '<div class="v622-score"><b>' + score + '<small>/3</small></b><div><strong>' + esc(chain.title) + '</strong>' +
      '<p>Рисковых решений: ' + record.risks.length + '. Теперь открыта основная языковая задача текущего вопроса.</p></div></div>' +
      '<div class="v622-complete-note"><b>' + (level === "expert" ? "Экспертный режим" : "Сменный режим") + '</b>' +
      '<span>Сначала управляем производственным риском, затем решаем языковую задачу.</span></div></div>';
  }

  function bindPanel(panel, stage, chain, record, level) {
    queryAll("[data-v622-option]", panel).forEach(function (button) {
      button.addEventListener("click", function () {
        if (record.selection) return;
        const index = Number(button.dataset.v622Option);
        const option = chain.steps[record.step].options[index];
        const correct = Boolean(option && option.correct);
        record.selection = {index: index, correct: correct, consequence: option ? option.consequence : ""};
        record.choices.push({step: record.step, index: index, correct: correct});
        if (correct) record.correct += 1;
        else record.risks.push({step: record.step, consequence: option ? option.consequence : ""});
        panel.innerHTML = stepPanel(chain, record, level);
        bindPanel(panel, stage, chain, record, level);
      });
    });
    const next = query("[data-v622-next]", panel);
    if (next) next.addEventListener("click", function () {
      if (!record.selection) return;
      if (record.step >= CHAIN_STEPS - 1) {
        record.done = true;
        record.selection = null;
        panel.innerHTML = completePanel(chain, record, level);
        panel.classList.add("complete");
        unlockStage(stage);
        return;
      }
      record.step += 1;
      record.selection = null;
      panel.innerHTML = stepPanel(chain, record, level);
      bindPanel(panel, stage, chain, record, level);
    });
  }

  function decorateCatalog() {
    const host = query(".v621-difficulty-panel") || query(".game-lab-summary");
    if (!host || query(".v622-catalog-panel")) return Boolean(host);
    host.insertAdjacentHTML("afterend",
      '<section class="v622-catalog-panel"><div><span>PRODUCTION DECISION CHAINS · v6.0.22</span>' +
      '<h2>На смене важен не один ответ, а порядок действий</h2><p>На уровнях Смена и Эксперт языковая практика сначала проходит через три последовательных производственных решения с видимыми последствиями.</p></div>' +
      '<div class="v622-family-list"><span>Andon / Line Stop</span><span>Quality containment</span><span>Supplier delay</span>' +
      '<span>Сварка</span><span>Окраска</span><span>Safety</span><span>Engineering change</span><span>Supplier escalation</span></div></section>');
    return true;
  }

  function decorateSession() {
    const shell = query(".game-session-shell");
    const stage = shell && query(".game-stage", shell);
    const snapshot = current();
    const session = snapshot.gameSessionV618;
    if (!stage || !session || !Array.isArray(session.items)) return false;
    const index = Number(snapshot.gameIndexV618 || 0);
    const item = session.items[index];
    if (!item) return false;
    const level = depth().effectiveDifficulty(index);
    if (!shouldChain(level)) {
      stage.classList.add("v622-training-pass");
      return true;
    }
    const scene = depth().detectScene(session.game_type, item);
    const family = familyFor(scene, session.game_type);
    const chain = CHAINS[family] || CHAINS.line_stop;
    const key = String(session.session_id || session.game_type) + ":" + index + ":" + level + ":" + family;
    const record = recordFor(key);
    let panel = query(".v622-chain-panel", stage);
    if (panel && panel.dataset.v622Key === key) return true;
    if (panel) panel.remove();
    stage.insertAdjacentHTML("afterbegin", '<section class="v622-chain-panel" data-v622-key="' + esc(key) + '"></section>');
    panel = query(".v622-chain-panel", stage);
    if (!panel) return false;
    if (record.done) {
      panel.innerHTML = completePanel(chain, record, level);
      panel.classList.add("complete");
      unlockStage(stage);
    } else {
      panel.innerHTML = stepPanel(chain, record, level);
      lockStage(stage);
      bindPanel(panel, stage, chain, record, level);
    }
    return true;
  }

  function decorate() {
    scheduled = false;
    if (String(current().view || "") !== "games") return;
    decorateCatalog();
    decorateSession();
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
      observer.observe(main, {childList: true, subtree: true});
    }
    document.addEventListener("mgc:state-change", scheduleDecorate);
    document.addEventListener("mgc:frontend-ready", scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register("decision-chains-v622", {
    chains: CHAINS,
    familyFor: familyFor,
    shouldChain: shouldChain,
    decorate: decorate,
    install: install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once: true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
