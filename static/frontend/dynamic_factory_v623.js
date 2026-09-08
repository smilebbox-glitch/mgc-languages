/* v6.0.23: dynamic factory scenarios — prior decisions change live factory state and subsequent context. */
(function (root) {
  "use strict";

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error("MGCFrontend runtime is missing");
  if (frontend.has("dynamic-factory-v623")) return;

  const scenarioStates = new Map();
  let installed = false;
  let observer = null;
  let scheduled = false;

  const CONFIG = Object.freeze({
    line_stop: {
      title: "Live Line Recovery",
      metrics: [
        {key:"atRisk", label:"Авто в зоне риска", max:12, bad:"high"},
        {key:"lineRisk", label:"Риск повторного stop", max:100, bad:"high", unit:"%"},
        {key:"restart", label:"Готовность restart", max:100, bad:"low", unit:"%"}
      ],
      initial:{atRisk:1, lineRisk:35, restart:25},
      intro:"Линия ещё управляема, но каждое следующее решение меняет масштаб и длительность остановки."
    },
    quality: {
      title: "Live Quality Containment",
      metrics: [
        {key:"atRisk", label:"Авто в suspect window", max:15, bad:"high"},
        {key:"containment", label:"Containment", max:100, bad:"low", unit:"%"},
        {key:"evidence", label:"Доказательность", max:100, bad:"low", unit:"%"}
      ],
      initial:{atRisk:2, containment:20, evidence:20},
      intro:"Граница дефекта пока не доказана. Ошибки увеличивают suspect window и объём сортировки."
    },
    logistics: {
      title: "Live Material Recovery",
      metrics: [
        {key:"runout", label:"Запас до run-out", max:120, bad:"low", unit:" мин"},
        {key:"lineRisk", label:"Риск line stop", max:100, bad:"high", unit:"%"},
        {key:"recovery", label:"Управляемость recovery", max:100, bad:"low", unit:"%"}
      ],
      initial:{runout:75, lineRisk:35, recovery:20},
      intro:"У линии есть ограниченное окно. Неполный recovery plan буквально сокращает доступное время."
    },
    welding: {
      title: "Live Body Shop State",
      metrics: [
        {key:"atRisk", label:"Кузова в риске", max:10, bad:"high"},
        {key:"evidence", label:"Process evidence", max:100, bad:"low", unit:"%"},
        {key:"restart", label:"Готовность restart", max:100, bad:"low", unit:"%"}
      ],
      initial:{atRisk:1, evidence:20, restart:20},
      intro:"Сварочный дефект может быстро уйти downstream. Решения меняют число подозрительных кузовов."
    },
    paint: {
      title: "Live Paint Recovery",
      metrics: [
        {key:"atRisk", label:"Кузова в риске", max:12, bad:"high"},
        {key:"evidence", label:"Process evidence", max:100, bad:"low", unit:"%"},
        {key:"restart", label:"Готовность к такту", max:100, bad:"low", unit:"%"}
      ],
      initial:{atRisk:2, evidence:15, restart:20},
      intro:"Повторяемый дефект поверхности размножается по партии, если containment или проверка процесса запаздывают."
    },
    safety: {
      title: "Live Safety State",
      metrics: [
        {key:"exposure", label:"Активная экспозиция", max:100, bad:"high", unit:"%"},
        {key:"barrier", label:"Надёжность барьера", max:100, bad:"low", unit:"%"},
        {key:"restart", label:"Safe restart", max:100, bad:"low", unit:"%"}
      ],
      initial:{exposure:45, barrier:30, restart:20},
      intro:"Near miss остаётся активным риском, пока не восстановлен барьер и не проверено безопасное состояние."
    },
    engineering: {
      title: "Live Change-Control State",
      metrics: [
        {key:"variantRisk", label:"Конфигурационный риск", max:100, bad:"high", unit:"%"},
        {key:"control", label:"Change control", max:100, bad:"low", unit:"%"},
        {key:"release", label:"Release readiness", max:100, bad:"low", unit:"%"}
      ],
      initial:{variantRisk:30, control:25, release:20},
      intro:"Неполное инженерное изменение начинает расходиться по BOM, WI, stock и производственным вариантам."
    },
    supplier: {
      title: "Live Supplier Dialogue",
      metrics: [
        {key:"clarity", label:"Ясность запроса", max:100, bad:"low", unit:"%"},
        {key:"containment", label:"Supplier containment", max:100, bad:"low", unit:"%"},
        {key:"confidence", label:"Уверенность в ответе", max:100, bad:"low", unit:"%"}
      ],
      initial:{clarity:30, containment:15, confidence:35},
      intro:"Поставщик реагирует на качество исходных данных. Размытая эскалация приводит к размытым ответам и потерянному времени."
    }
  });

  function legacy() { return frontend.get("legacy-app"); }
  function state() { return frontend.get("app-state"); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }
  function clamp(value, min, max) { return Math.max(min, Math.min(max, Number(value || 0))); }

  function familyFromKey(key) {
    const parts = String(key || "").split(":");
    const family = parts[parts.length - 1];
    return CONFIG[family] ? family : "line_stop";
  }

  function createState(key, family) {
    const cfg = CONFIG[family] || CONFIG.line_stop;
    return {
      key:key,
      family:family,
      values:Object.assign({}, cfg.initial),
      processed:Object.create(null),
      history:[],
      latest:null,
      branch:"initial"
    };
  }

  function stateFor(key, family) {
    if (!scenarioStates.has(key)) {
      scenarioStates.set(key, createState(key, family));
      if (scenarioStates.size > 100) scenarioStates.delete(scenarioStates.keys().next().value);
    }
    return scenarioStates.get(key);
  }

  function adjust(model, key, delta) {
    const cfg = CONFIG[model.family] || CONFIG.line_stop;
    const descriptor = cfg.metrics.find(function (metric) { return metric.key === key; });
    const max = descriptor ? descriptor.max : 100;
    model.values[key] = clamp(Number(model.values[key] || 0) + delta, 0, max);
  }

  function event(title, detail, severity, reply) {
    return {title:title, detail:detail, severity:severity || "watch", reply:reply || null};
  }

  function supplierReply(zh, pinyin, en, ru) {
    return {zh:zh, pinyin:pinyin, en:en, ru:ru};
  }

  function applyLineStop(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "lineRisk", -20); adjust(model, "restart", 10);
        return event("Andon сработал вовремя", "Следующий автомобиль не вошёл в зону риска. Команда получила контролируемое окно для containment.", "good");
      }
      if (index === 0) {
        adjust(model, "atRisk", 4); adjust(model, "lineRisk", 25); adjust(model, "restart", -10);
        return event("Риск ушёл downstream", "Пока оператор завершал такт, ещё 4 автомобиля вошли в suspect window. Второй шаг теперь начинается с расширенного containment.", "critical");
      }
      adjust(model, "atRisk", 2); adjust(model, "lineRisk", 15); adjust(model, "restart", -10);
      return event("Эскалация ушла в поиск виновного", "Процесс не был защищён сразу: два следующих автомобиля требуют проверки, а причина всё ещё не локализована.", "risk");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "lineRisk", -15); adjust(model, "restart", 30);
        return event("Граница риска доказана", "Last known good и владелец определены. Перезапуск теперь зависит от фактического first-off, а не от предположения.", "good");
      }
      if (index === 1) {
        adjust(model, "atRisk", 3); adjust(model, "lineRisk", 20); adjust(model, "restart", -5);
        return event("Преждевременный restart", "После запуска без доказанной границы три автомобиля снова попали в зону проверки. Риск повторного stop вырос.", "critical");
      }
      adjust(model, "lineRisk", 12); adjust(model, "restart", -10);
      return event("Containment затянулся", "Команда ждёт отчёт вместо оперативного решения. Потеря времени увеличивает давление на последующий restart.", "risk");
    }
    if (correct) {
      adjust(model, "lineRisk", -25); adjust(model, "restart", 50);
      return event("Verified restart", "First-off подтверждён, контроль назначен. Линия возвращается в работу с проверяемым основанием.", "good");
    }
    adjust(model, "lineRisk", index === 1 ? 28 : 18); adjust(model, "restart", -20); adjust(model, "atRisk", index === 1 ? 2 : 0);
    return event("Restart остаётся нестабильным", index === 1 ? "Погоня за объёмом вытеснила quality gate: повторный stop теперь вероятнее." : "Решение опирается на мнение без first-off evidence; процесс остаётся под наблюдением.", "critical");
  }

  function applyQuality(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "containment", 45); adjust(model, "evidence", 10);
        return event("Suspect window заморожен", "Containment выполнен до дальнейшего распространения. Следующий шаг может работать с ограниченным набором автомобилей.", "good");
      }
      const growth = index === 1 ? 6 : 8;
      adjust(model, "atRisk", growth); adjust(model, "containment", -10);
      return event("Дефект продолжил распространяться", "Пока containment не был выполнен, ещё " + growth + " автомобилей вошли в suspect window. Traceability теперь сложнее и дороже.", "critical");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "containment", 15); adjust(model, "evidence", 45);
        return event("Traceability восстановила границу", "Партия, временное окно и last known good определены. Root-cause работа получает надёжную базу.", "good");
      }
      adjust(model, "atRisk", index === 0 ? 3 : 4); adjust(model, "evidence", -5);
      return event("Граница остаётся предположением", "Недостаточная traceability расширяет сортировку. Следующий шаг должен закрывать причину при более слабой доказательной базе.", "risk");
    }
    if (correct) {
      adjust(model, "containment", 20); adjust(model, "evidence", 40);
      return event("Проблема получила техническое закрытие", "Root cause, corrective action, owner и effectiveness check формируют управляемое предотвращение повторения.", "good");
    }
    if (index === 0) { adjust(model, "containment", 8); adjust(model, "evidence", 5); }
    else { adjust(model, "evidence", -10); }
    return event("Containment есть, предотвращения нет", index === 0 ? "Сортировка защищает текущую партию, но повторение процесса остаётся открытым." : "Устное обещание не создаёт проверяемой причины и effectiveness check.", "risk");
  }

  function applyLogistics(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "runout", 10); adjust(model, "lineRisk", -10); adjust(model, "recovery", 18);
        return event("Run-out стал измеримым", "Команда видит реальное окно по запасу и может управлять модельным миксом до прибытия материала.", "good");
      }
      if (index === 1) { adjust(model, "runout", -25); adjust(model, "lineRisk", 22); }
      else { adjust(model, "runout", -10); adjust(model, "lineRisk", 12); }
      adjust(model, "recovery", -5);
      return event("Окно до дефицита сократилось", index === 1 ? "Ожидание плановой поставки съело 25 минут доступного запаса. Следующий шаг уже работает под риском line stop." : "Линия была остановлена без расчёта; recovery теряет время и производственную гибкость.", "critical");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "runout", 30); adjust(model, "lineRisk", -22); adjust(model, "recovery", 42);
        return event("Recovery получил несколько рычагов", "Expedite, альтернативный маршрут и approved stock добавили управляемое время до run-out.", "good");
      }
      if (index === 2) { adjust(model, "runout", -20); adjust(model, "lineRisk", 32); adjust(model, "recovery", -15); }
      else { adjust(model, "runout", -15); adjust(model, "lineRisk", 16); }
      return event("Recovery остаётся хрупким", index === 2 ? "Неутверждённая замена создаёт одновременно логистический, BOM и quality risk." : "Сообщение «срочно» не создало маршрута, количества или подтверждённого времени.", "critical");
    }
    if (correct) {
      adjust(model, "lineRisk", -25); adjust(model, "recovery", 38);
      return event("Поставка стала управляемым обещанием", "ETA, quantity, owner, control point и fallback позволяют увидеть отклонение до line stop.", "good");
    }
    adjust(model, "runout", index === 1 ? -10 : -20); adjust(model, "lineRisk", index === 1 ? 15 : 25); adjust(model, "recovery", -8);
    return event("Статус не защищает линию", index === 1 ? "Номер транспорта не заменяет ETA и decision owner." : "Фраза «в пути» скрывает фактическое время и не даёт следующей контрольной точки.", "risk");
  }

  function applyBodyProcess(model, step, index, correct, paint) {
    if (step === 0) {
      if (correct) {
        adjust(model, "evidence", 15); adjust(model, "restart", 8);
        return event(paint ? "Кузова удержаны" : "Подозрительные кузова изолированы", paint ? "Дефект поверхности больше не размножается по потоку; границу можно доказать." : "Сварочный риск остановлен до ухода дополнительных кузовов downstream.", "good");
      }
      const growth = index === 2 ? 5 : 3;
      adjust(model, "atRisk", growth); adjust(model, "restart", -8);
      return event("Suspect window расширился", "Из-за задержки containment ещё " + growth + " кузовов требуют проверки. Последующий recovery становится длиннее.", "critical");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "evidence", 50); adjust(model, "restart", 20);
        return event("Process evidence найден", paint ? "Материал, spray parameters, robot и booth conditions проверяются как одна система." : "Параметры сварки, электроды и fixture дают проверяемую гипотезу причины.", "good");
      }
      adjust(model, "evidence", -8); adjust(model, "restart", -8);
      return event("Проверка ушла в слабый сигнал", paint ? "Один цвет или имя оператора не объясняют системный дефект покрытия." : "Внешний вид точки или скорость линии не подтверждают стабильность сварочного процесса.", "risk");
    }
    if (correct) {
      adjust(model, "evidence", 30); adjust(model, "restart", 55);
      return event("First-off подтвердил recovery", paint ? "Surface check и усиленный контроль позволяют вернуть нормальный takt." : "Repair/first-off и параметры процесса подтверждают управляемый restart.", "good");
    }
    adjust(model, "restart", -25); adjust(model, "evidence", -5);
    return event("Restart не доказан", paint ? "Работа робота или температура камеры не доказывают качество поверхности." : "Alarm reset или ускорение линии не подтверждают качество сварного соединения.", "critical");
  }

  function applySafety(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "exposure", -35); adjust(model, "restart", 10);
        return event("Опасное взаимодействие остановлено", "Экспозиция прекращена до разбора причины. Команда может перейти к восстановлению барьера.", "good");
      }
      adjust(model, "exposure", index === 0 ? 25 : 18); adjust(model, "restart", -10);
      return event("Near miss остаётся активным", "Документирование или передача следующей смене не убрали текущую экспозицию риска.", "critical");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "exposure", -20); adjust(model, "barrier", 55); adjust(model, "restart", 20);
        return event("Барьер восстановлен", "Разделение потоков и visibility снижают вероятность повторения, а не просто напоминают быть осторожнее.", "good");
      }
      adjust(model, "barrier", -8); adjust(model, "exposure", 8);
      return event("Симптом исправлен, система нет", "Слабое организационное действие оставляет исходный маршрут конфликта людей и техники.", "risk");
    }
    if (correct) {
      adjust(model, "barrier", 25); adjust(model, "restart", 55); adjust(model, "exposure", -20);
      return event("Safe state подтверждён", "Барьер проверен, команда проинформирована, участок возвращается в работу на проверяемом основании.", "good");
    }
    adjust(model, "restart", -30); adjust(model, "exposure", 15);
    return event("Перезапуск преждевременен", "Время или свободный проход не доказывают эффективность защитных мер.", "critical");
  }

  function applyEngineering(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "variantRisk", -12); adjust(model, "control", 35);
        return event("Change scope определён", "Revision, reason и effective point ограничивают изменение конкретным вариантом и временной точкой.", "good");
      }
      adjust(model, "variantRisk", index === 0 ? 28 : 20); adjust(model, "control", -8);
      return event("Изменение начало расходиться", index === 0 ? "BOM изменён без effective point: разные функции могут использовать разные конфигурации." : "Письмо ушло на линию до инженерного release, создавая неуправляемое применение.", "critical");
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "variantRisk", -15); adjust(model, "control", 35); adjust(model, "release", 20);
        return event("Downstream impact виден", "BOM, drawing, WI, tooling, quality plan и stock теперь входят в один change scope.", "good");
      }
      adjust(model, "variantRisk", 22); adjust(model, "release", -8);
      return event("Downstream gap обнаружится позже", "Часть производственных зависимостей осталась вне оценки; риск version mismatch растёт.", "risk");
    }
    if (correct) {
      adjust(model, "variantRisk", -20); adjust(model, "control", 25); adjust(model, "release", 55);
      return event("Controlled release готов", "Approved revision, effective point, old-stock disposition и first verification создают однозначную конфигурацию.", "good");
    }
    adjust(model, "variantRisk", 18); adjust(model, "release", -20);
    return event("Release остаётся неоднозначным", "Устная договорённость или удаление файла не создают change record и границу применения.", "critical");
  }

  function applySupplier(model, step, index, correct) {
    if (step === 0) {
      if (correct) {
        adjust(model, "clarity", 50); adjust(model, "confidence", 20);
        return event("Поставщик понял объект проблемы", "Part/lot, quantity и место обнаружения позволяют начать traceability без дополнительного раунда вопросов.", "good",
          supplierReply("已收到。请发送零件号、批次照片和缺陷数量，我们立即核查。", "Yǐ shōudào. Qǐng fāsòng língjiànhào, pīcì zhàopiàn hé quēxiàn shùliàng, wǒmen lìjí héchá.", "Received. Send the part number, lot photo, and defect quantity; we will check immediately.", "Получено. Отправьте номер детали, фото партии и количество дефектов; начинаем проверку."));
      }
      adjust(model, "clarity", index === 0 ? -18 : -10); adjust(model, "confidence", index === 0 ? -20 : -10);
      return event("Поставщик запросил уточнение", index === 0 ? "Фраза звучит как обвинение, но не содержит данных для traceability. Потерян один коммуникационный цикл." : "Срочность понятна, но номер детали и партия отсутствуют; поставщик не может локализовать материал.", "risk",
        supplierReply("请提供零件号、批次和具体缺陷信息，否则无法确认范围。", "Qǐng tígōng língjiànhào, pīcì hé jùtǐ quēxiàn xìnxī, fǒuzé wúfǎ quèrèn fànwéi.", "Please provide the part number, lot, and specific defect details; otherwise we cannot confirm the scope.", "Предоставьте номер детали, партию и конкретное описание дефекта; иначе масштаб подтвердить нельзя."));
    }
    if (step === 1) {
      if (correct) {
        adjust(model, "containment", 55); adjust(model, "confidence", 18);
        return event("Supplier containment подтверждён", "Поставщик изолирует stock, сортирует материал и даёт ETA certified lot до завершения root cause.", "good",
          supplierReply("我们现在隔离库存并安排全检，合格批次预计今晚发出。", "Wǒmen xiànzài gélí kùcún bìng ānpái quánjiǎn, hégé pīcì yùjì jīnwǎn fāchū.", "We are containing stock and arranging 100% inspection now. The certified lot is expected to ship tonight.", "Мы изолируем запас и запускаем 100% проверку; проверенную партию планируем отправить сегодня вечером."));
      }
      adjust(model, "containment", index === 0 ? -12 : -22); adjust(model, "confidence", index === 2 ? -22 : -8);
      return event("Текущий риск не закрыт", index === 0 ? "Поставщик готовит 8D, но завод остаётся без временного containment и certified material." : "Коммерческий разговор заменил техническую защиту текущего производства.", "critical",
        supplierReply("根本原因分析需要时间，请确认你们当前是否需要临时筛选方案。", "Gēnběn yuányīn fēnxī xūyào shíjiān, qǐng quèrèn nǐmen dāngqián shìfǒu xūyào línshí shāixuǎn fāng'àn.", "Root-cause analysis will take time. Please confirm whether you need a temporary sorting plan now.", "Анализ корневой причины займёт время. Подтвердите, нужен ли сейчас временный план сортировки."));
    }
    if (correct) {
      adjust(model, "clarity", 15); adjust(model, "confidence", 32); adjust(model, "containment", 18);
      return event("Эскалация стала управляемой", "Owner, deadlines и evidence создают конкретный следующий цикл вместо бесконечного чата.", "good",
        supplierReply("已确认负责人和时间节点，临时措施证据将在两小时内发送。", "Yǐ quèrèn fùzérén hé shíjiān jiédiǎn, línshí cuòshī zhèngjù jiāng zài liǎng xiǎoshí nèi fāsòng.", "Owner and timing are confirmed. Containment evidence will be sent within two hours.", "Владелец и сроки подтверждены. Доказательство containment будет отправлено в течение двух часов."));
    }
    adjust(model, "clarity", index === 1 ? -8 : -12); adjust(model, "confidence", index === 1 ? -15 : -22);
    return event("Диалог снова стал размытым", "Без owner, deadline и evidence следующий ответ поставщика нельзя проверить по сроку или результату.", "risk",
      supplierReply("我们会尽快回复。", "Wǒmen huì jǐnkuài huífù.", "We will reply as soon as possible.", "Мы ответим как можно скорее."));
  }

  function applyDecision(model, step, index, correct) {
    let outcome;
    if (model.family === "quality") outcome = applyQuality(model, step, index, correct);
    else if (model.family === "logistics") outcome = applyLogistics(model, step, index, correct);
    else if (model.family === "welding") outcome = applyBodyProcess(model, step, index, correct, false);
    else if (model.family === "paint") outcome = applyBodyProcess(model, step, index, correct, true);
    else if (model.family === "safety") outcome = applySafety(model, step, index, correct);
    else if (model.family === "engineering") outcome = applyEngineering(model, step, index, correct);
    else if (model.family === "supplier") outcome = applySupplier(model, step, index, correct);
    else outcome = applyLineStop(model, step, index, correct);
    model.latest = outcome;
    model.branch = outcome.severity;
    model.history.push({step:step, index:index, correct:correct, outcome:outcome});
    if (model.history.length > 6) model.history.shift();
  }

  function badness(model, descriptor) {
    const value = Number(model.values[descriptor.key] || 0);
    const ratio = descriptor.max ? value / descriptor.max : 0;
    return descriptor.bad === "low" ? 1 - ratio : ratio;
  }

  function overallStatus(model) {
    const cfg = CONFIG[model.family] || CONFIG.line_stop;
    const average = cfg.metrics.reduce(function (sum, metric) { return sum + badness(model, metric); }, 0) / cfg.metrics.length;
    if (average >= 0.64) return {label:"Критичный", cls:"critical"};
    if (average >= 0.38) return {label:"Под контролем", cls:"watch"};
    return {label:"Стабильный", cls:"stable"};
  }

  function metricMarkup(model, descriptor) {
    const value = Number(model.values[descriptor.key] || 0);
    const pct = clamp((value / descriptor.max) * 100, 0, 100);
    const display = Math.round(value) + (descriptor.unit || "");
    return '<div class="v623-metric"><div><span>' + esc(descriptor.label) + '</span><b>' + esc(display) + '</b></div>' +
      '<i><em style="width:' + pct.toFixed(1) + '%"></em></i></div>';
  }

  function replyMarkup(reply) {
    if (!reply) return "";
    const language = String(current().language || "chinese");
    if (language === "chinese") {
      return '<div class="v623-supplier-reply"><span>Ответ поставщика · 中文</span><b>' + esc(reply.zh) + '</b><i>' + esc(reply.pinyin) + '</i><small>' + esc(reply.ru) + '</small></div>';
    }
    return '<div class="v623-supplier-reply"><span>Supplier response</span><b>' + esc(reply.en) + '</b><small>' + esc(reply.ru) + '</small></div>';
  }

  function eventMarkup(outcome, compact) {
    if (!outcome) return "";
    return '<div class="v623-event ' + esc(outcome.severity) + (compact ? ' compact' : '') + '"><span>' +
      (outcome.severity === "good" ? "СЦЕНАРИЙ СТАБИЛИЗИРУЕТСЯ" : outcome.severity === "critical" ? "СЦЕНАРИЙ УХУДШИЛСЯ" : "СЦЕНАРИЙ ИЗМЕНИЛСЯ") +
      '</span><b>' + esc(outcome.title) + '</b><p>' + esc(outcome.detail) + '</p>' + replyMarkup(outcome.reply) + '</div>';
  }

  function timelineMarkup(model) {
    const items = model.history.slice(-3);
    if (!items.length) return "";
    return '<div class="v623-timeline"><span>Последствия предыдущих решений</span>' + items.map(function (entry) {
      return '<div class="' + (entry.correct ? "good" : "risk") + '"><b>Шаг ' + (entry.step + 1) + '</b><small>' + esc(entry.outcome.title) + '</small></div>';
    }).join("") + '</div>';
  }

  function dynamicPanelMarkup(model, done) {
    const cfg = CONFIG[model.family] || CONFIG.line_stop;
    const status = overallStatus(model);
    return '<div class="v623-head"><div><span>LIVE FACTORY STATE · v6.0.23</span><h2>' + esc(cfg.title) + '</h2>' +
      '<p>' + esc(cfg.intro) + '</p></div><b class="v623-status ' + status.cls + '">' + esc(status.label) + '</b></div>' +
      '<div class="v623-metrics">' + cfg.metrics.map(function (metric) { return metricMarkup(model, metric); }).join("") + '</div>' +
      eventMarkup(model.latest, false) + timelineMarkup(model) +
      (done ? '<div class="v623-final"><b>Состояние переносится в основную языковую задачу</b><span>Вы уже не отвечаете в вакууме: текущая задача открывается после конкретной истории решений и их производственных последствий.</span></div>' : '') +
      '<small class="v623-no-xp">Dynamic Factory Scenario не начисляет дополнительный XP и не меняет серверный лимит пяти ответов.</small>';
  }

  function parseStep(panel) {
    const label = query(".v622-chain-question > span", panel);
    const match = label && String(label.textContent || "").match(/(\d+)/);
    return match ? Math.max(0, Number(match[1]) - 1) : -1;
  }

  function consumeChoice(panel, model) {
    const selected = query(".v622-chain-options [data-v622-option].selected", panel);
    if (!selected) return false;
    const step = parseStep(panel);
    if (step < 0) return false;
    const index = Number(selected.dataset.v622Option);
    const token = step + ":" + index;
    if (model.processed[token]) return false;
    model.processed[token] = true;
    applyDecision(model, step, index, selected.classList.contains("correct"));
    return true;
  }

  function branchContext(panel, model) {
    const question = query(".v622-chain-question", panel);
    if (!question) return;
    const existing = query(".v623-branch-context", question);
    if (existing) existing.remove();
    const step = parseStep(panel);
    if (step <= 0 || !model.latest) return;
    question.insertAdjacentHTML("afterbegin", '<div class="v623-branch-context"><span>Состояние после предыдущего решения</span>' +
      '<b>' + esc(model.latest.title) + '</b><p>' + esc(model.latest.detail) + '</p></div>');
  }

  function decorateCatalog() {
    const host = query(".v622-catalog-panel") || query(".v621-difficulty-panel");
    if (!host || query(".v623-catalog-panel")) return Boolean(host);
    host.insertAdjacentHTML("afterend", '<section class="v623-catalog-panel"><div><span>DYNAMIC FACTORY SCENARIOS · v6.0.23</span>' +
      '<h2>Одно решение меняет следующий производственный эпизод</h2><p>На уровнях Смена и Эксперт последствия решений теперь переносятся дальше: растёт suspect window, меняется run-out, качество supplier response и готовность к restart.</p></div>' +
      '<div class="v623-catalog-flow"><span>Решение</span><b>→</b><span>Состояние завода</span><b>→</b><span>Новый контекст</span><b>→</b><span>Следующее решение</span></div></section>');
    return true;
  }

  function decorateSession() {
    const shell = query(".game-session-shell");
    const stage = shell && query(".game-stage", shell);
    const panel = stage && query(".v622-chain-panel", stage);
    if (!stage || !panel || !panel.dataset.v622Key) return false;
    const key = panel.dataset.v622Key;
    const family = familyFromKey(key);
    const model = stateFor(key, family);
    consumeChoice(panel, model);
    branchContext(panel, model);
    const done = Boolean(query(".v622-complete", panel));
    let live = query(".v623-dynamic-panel", stage);
    if (!live || live.dataset.v623Key !== key) {
      if (live) live.remove();
      panel.insertAdjacentHTML("afterend", '<section class="v623-dynamic-panel" data-v623-key="' + esc(key) + '"></section>');
      live = query(".v623-dynamic-panel", stage);
    }
    if (!live) return false;
    live.innerHTML = dynamicPanelMarkup(model, done);
    live.classList.toggle("complete", done);
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
      observer.observe(main, {childList:true, subtree:true, attributes:true, attributeFilter:["class"]});
    }
    document.addEventListener("mgc:state-change", scheduleDecorate);
    document.addEventListener("mgc:frontend-ready", scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register("dynamic-factory-v623", {
    config:CONFIG,
    familyFromKey:familyFromKey,
    decorate:decorate,
    install:install
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, {once:true});
  else install();
})(typeof window !== "undefined" ? window : globalThis);
