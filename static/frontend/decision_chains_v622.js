/* v6.0.22: production decision chains — multi-step automotive decisions with consequences and bilingual shop-floor language. */
(function (root) {
  'use strict';

  const frontend = root.MGCFrontend;
  if (!frontend) throw new Error('MGCFrontend runtime is missing');
  if (frontend.has('decision-chains-v622')) return;

  const CHAIN_STEPS = 3;
  const records = new Map();
  let installed = false;
  let observer = null;
  let scheduled = false;

  const CHAINS = Object.freeze({
    line_stop: {
      title:'Andon / Line Stop',
      subtitle:'Остановить риск, стабилизировать процесс и разрешить перезапуск только после проверки.',
      steps:[
        {
          prompt:'На посту обнаружен риск качества, который может уйти на следующий автомобиль. Первое действие?',
          options:[
            {label:'Продолжить до конца такта и сообщить позже', correct:false, consequence:'Подозрительные автомобили продолжают двигаться по потоку, зона риска растёт.'},
            {label:'Активировать Andon и остановить рискованную операцию', correct:true, consequence:'Риск локализован в точке возникновения, команда получает время на проверку.'},
            {label:'Сразу искать виновного оператора', correct:false, consequence:'Время теряется на персонализацию проблемы, а процесс остаётся неконтролируемым.'}
          ],
          phrase:{
            chinese:'请先停止有风险的工序并启动安灯。',
            pinyin:'Qǐng xiān tíngzhǐ yǒu fēngxiǎn de gōngxù bìng qǐdòng āndēng.',
            english:'Please stop the risky operation first and activate the Andon.',
            russian:'Сначала остановите рискованную операцию и активируйте Andon.'
          }
        },
        {
          prompt:'Линия остановлена. Что нужно сделать до попытки перезапуска?',
          options:[
            {label:'Проверить последнюю годную деталь, изолировать подозрительное и назначить владельца', correct:true, consequence:'Граница дефекта и ответственность определены, дальнейшее решение опирается на факты.'},
            {label:'Перезапустить линию, если визуально всё выглядит нормально', correct:false, consequence:'Без подтверждённой границы дефекта возможен повторный выпуск несоответствия.'},
            {label:'Ждать только письменного отчёта конца смены', correct:false, consequence:'Остановка затягивается, а оперативное containment не выполняется.'}
          ],
          phrase:{
            chinese:'请确认最后一个合格件，并隔离所有可疑件。',
            pinyin:'Qǐng quèrèn zuìhòu yí ge hégé jiàn, bìng gélí suǒyǒu kěyí jiàn.',
            english:'Confirm the last known good part and segregate all suspect parts.',
            russian:'Подтвердите последнюю годную деталь и изолируйте все подозрительные.'
          }
        },
        {
          prompt:'Проверка завершена. Какое условие достаточно для управляемого перезапуска?',
          options:[
            {label:'Есть подтверждённое исправление, first-off проверен, владелец и контроль определены', correct:true, consequence:'Перезапуск имеет проверяемое основание и усиленный контроль после восстановления.'},
            {label:'Мастер считает, что проблема больше не повторится', correct:false, consequence:'Мнение без доказательства не закрывает риск повторного дефекта.'},
            {label:'Нужно наверстать план, поэтому запускаем без first-off', correct:false, consequence:'Давление по объёму вытесняет quality gate и повышает риск повторной остановки.'}
          ],
          phrase:{
            chinese:'首件确认合格后才能恢复生产。',
            pinyin:'Shǒujiàn quèrèn hégé hòu cái néng huīfù shēngchǎn.',
            english:'Production may resume only after the first-off part is confirmed OK.',
            russian:'Производство можно возобновить только после подтверждения годности first-off.'
          }
        }
      ]
    },
    quality: {
      title:'Quality Escalation',
      subtitle:'Containment → scope & traceability → root cause & corrective action.',
      steps:[
        {
          prompt:'На автомобиле найден повторяющийся дефект. Что важнее сделать первым?',
          options:[
            {label:'Изолировать затронутые и потенциально затронутые единицы', correct:true, consequence:'Containment предотвращает дальнейшее распространение несоответствия.'},
            {label:'Сразу потребовать финальный 8D', correct:false, consequence:'Root cause важен, но без containment дефект продолжает уходить дальше.'},
            {label:'Снизить критерий приемки на смену', correct:false, consequence:'Изменение критерия без инженерного основания маскирует проблему.'}
          ],
          phrase:{
            chinese:'请立即隔离受影响和可疑的车辆。',
            pinyin:'Qǐng lìjí gélí shòu yǐngxiǎng hé kěyí de chēliàng.',
            english:'Immediately contain the affected and potentially affected vehicles.',
            russian:'Немедленно изолируйте затронутые и потенциально затронутые автомобили.'
          }
        },
        {
          prompt:'Containment выполнен. Как определить реальный масштаб проблемы?',
          options:[
            {label:'Проверить traceability, время возникновения, партию и last known good', correct:true, consequence:'Граница риска строится по прослеживаемости, а не по предположению.'},
            {label:'Проверить только один следующий автомобиль', correct:false, consequence:'Один образец не подтверждает границу партии или временного окна.'},
            {label:'Считать затронутой только первую найденную единицу', correct:false, consequence:'Повторяемый дефект может уже находиться в незавершённом производстве.'}
          ],
          phrase:{
            chinese:'请确认追溯信息、批次和最后一个合格件。',
            pinyin:'Qǐng quèrèn zhuīsù xìnxī, pīcì hé zuìhòu yí ge hégé jiàn.',
            english:'Confirm traceability, the batch, and the last known good unit.',
            russian:'Подтвердите прослеживаемость, партию и последнюю заведомо годную единицу.'
          }
        },
        {
          prompt:'Масштаб подтверждён. Что закрывает проблему на уровне процесса?',
          options:[
            {label:'Подтверждённая root cause, corrective action, проверка эффективности и владелец', correct:true, consequence:'Проблема получает техническое закрытие и контроль эффективности действия.'},
            {label:'Только сортировка всей партии', correct:false, consequence:'Сортировка защищает клиента, но не устраняет причину повторения.'},
            {label:'Устное обещание не допустить повторения', correct:false, consequence:'Без причины, действия и проверки эффективности риск остаётся неконтролируемым.'}
          ],
          phrase:{
            chinese:'请提供根本原因、纠正措施和效果验证。',
            pinyin:'Qǐng tígōng gēnběn yuányīn, jiūzhèng cuòshī hé xiàoguǒ yànzhèng.',
            english:'Provide the root cause, corrective action, and effectiveness verification.',
            russian:'Предоставьте корневую причину, корректирующее действие и проверку эффективности.'
          }
        }
      ]
    },
    logistics: {
      title:'Material Shortage',
      subtitle:'Run-out risk → recovery route → ETA, owner and line protection.',
      steps:[
        {
          prompt:'Поставщик сообщает о задержке критичного компонента. Что проверить сначала?',
          options:[
            {label:'Фактический остаток, расход, точку run-out и затронутые модели', correct:true, consequence:'Команда понимает реальное окно до дефицита и может приоритизировать действия.'},
            {label:'Сразу остановить всю сборку', correct:false, consequence:'Без расчёта run-out можно создать ненужную потерю производства.'},
            {label:'Ждать плановую поставку без пересчёта', correct:false, consequence:'Скрытый дефицит проявится слишком поздно для управляемого восстановления.'}
          ],
          phrase:{
            chinese:'请确认库存、消耗速度和预计断料时间。',
            pinyin:'Qǐng quèrèn kùcún, xiāohào sùdù hé yùjì duànliào shíjiān.',
            english:'Confirm stock, consumption rate, and the estimated run-out time.',
            russian:'Подтвердите запас, скорость расхода и ожидаемое время исчерпания.'
          }
        },
        {
          prompt:'Run-out подтверждён. Как строить recovery plan?',
          options:[
            {label:'Проверить expedite, альтернативный маршрут, доступный approved stock и приоритет моделей', correct:true, consequence:'Recovery plan использует несколько управляемых рычагов и защищает линию.'},
            {label:'Отправить поставщику только сообщение «срочно»', correct:false, consequence:'Без количества, маршрута и времени запрос не превращается в исполнимый план.'},
            {label:'Самостоятельно заменить компонент на похожий', correct:false, consequence:'Неутверждённая замена создаёт риск BOM, качества и сертификации.'}
          ],
          phrase:{
            chinese:'请确认加急方案、替代运输路线和可用合格库存。',
            pinyin:'Qǐng quèrèn jiājí fāng'àn, tìdài yùnshū lùxiàn hé kěyòng hégé kùcún.',
            english:'Confirm the expedite plan, alternative transport route, and available approved stock.',
            russian:'Подтвердите expedite-план, альтернативный маршрут и доступный утверждённый запас.'
          }
        },
        {
          prompt:'Recovery plan согласован. Какая информация должна остаться в управлении смены?',
          options:[
            {label:'Подтверждённый ETA, количество, владелец, контрольная точка и решение при отклонении', correct:true, consequence:'План становится измеримым, а отклонение обнаруживается до фактического line stop.'},
            {label:'Только номер машины перевозчика', correct:false, consequence:'Номер транспорта не даёт управляемого ETA и ответственности за отклонение.'},
            {label:'Фраза «поставка в пути»', correct:false, consequence:'Статус без времени, количества и владельца не защищает производство.'}
          ],
          phrase:{
            chinese:'请确认到达时间、数量、负责人和下一检查点。',
            pinyin:'Qǐng quèrèn dàodá shíjiān, shùliàng, fùzérén hé xià yí ge jiǎnchá diǎn.',
            english:'Confirm ETA, quantity, owner, and the next control point.',
            russian:'Подтвердите ETA, количество, владельца и следующую контрольную точку.'
          }
        }
      ]
    },
    welding: {
      title:'Body Shop Containment',
      subtitle:'Подозрительный кузов → параметры/оснастка → repair & verified restart.',
      steps:[
        {
          prompt:'На кузове обнаружен нестабильный сварной контакт. Первое решение?',
          options:[
            {label:'Изолировать кузова с момента last known good и остановить рискованную операцию', correct:true, consequence:'Подозрительный диапазон удерживается до подтверждения качества.'},
            {label:'Добавить ещё одну сварочную точку вручную без оценки', correct:false, consequence:'Несогласованное изменение процесса не доказывает соответствие конструкции.'},
            {label:'Отправить кузов дальше и проверить на финальном контроле', correct:false, consequence:'Дефект уходит downstream, а стоимость исправления и объём риска растут.'}
          ],
          phrase:{
            chinese:'请隔离可疑车身并停止有风险的焊接工序。',
            pinyin:'Qǐng gélí kěyí chēshēn bìng tíngzhǐ yǒu fēngxiǎn de hànjiē gōngxù.',
            english:'Contain the suspect bodies and stop the risky welding operation.',
            russian:'Изолируйте подозрительные кузова и остановите рискованную сварочную операцию.'
          }
        },
        {
          prompt:'Что проверять для локализации причины в сварочном процессе?',
          options:[
            {label:'Ток/время/усилие, состояние электродов, позиционирование и fixture', correct:true, consequence:'Проверяются параметры процесса и геометрические причины нестабильности.'},
            {label:'Только внешний вид одной точки', correct:false, consequence:'Визуальный признак не подтверждает стабильность параметров соединения.'},
            {label:'Только скорость конвейера', correct:false, consequence:'Скорость может влиять на процесс, но не заменяет проверку сварочных параметров и оснастки.'}
          ],
          phrase:{
            chinese:'请检查焊接参数、电极状态和夹具定位。',
            pinyin:'Qǐng jiǎnchá hànjiē cānshù, diànjí zhuàngtài hé jiājù dìngwèi.',
            english:'Check the welding parameters, electrode condition, and fixture location.',
            russian:'Проверьте параметры сварки, состояние электродов и позиционирование оснастки.'
          }
        },
        {
          prompt:'После корректировки процесса что требуется перед серийным продолжением?',
          options:[
            {label:'Проверенный repair/first-off и подтверждение параметров контроля', correct:true, consequence:'Перезапуск подтверждён фактическим результатом и стабильными параметрами.'},
            {label:'Только сброс alarm робота', correct:false, consequence:'Сброс alarm восстанавливает оборудование, но не подтверждает качество соединения.'},
            {label:'Увеличить темп для компенсации остановки', correct:false, consequence:'Повышение темпа сразу после нестабильности увеличивает риск повторения.'}
          ],
          phrase:{
            chinese:'首件和焊接参数确认合格后再继续生产。',
            pinyin:'Shǒujiàn hé hànjiē cānshù quèrèn hégé hòu zài jìxù shēngchǎn.',
            english:'Continue production only after the first-off and welding parameters are confirmed OK.',
            russian:'Продолжайте производство только после подтверждения first-off и параметров сварки.'
          }
        }
      ]
    },
    paint: {
      title:'Paint Process Recovery',
      subtitle:'Hold → process parameter check → rework/first-off confirmation.',
      steps:[
        {
          prompt:'На нескольких кузовах появился повторяющийся дефект покрытия. Что делать первым?',
          options:[
            {label:'Удержать затронутые кузова и определить временную границу дефекта', correct:true, consequence:'Дефект не уходит дальше, а зона риска становится измеримой.'},
            {label:'Полировать все кузова без классификации дефекта', correct:false, consequence:'Rework до понимания дефекта может скрыть симптом и потерять данные о процессе.'},
            {label:'Продолжить до конца партии', correct:false, consequence:'Повторяемый дефект размножается на дополнительные автомобили.'}
          ],
          phrase:{
            chinese:'请先扣留受影响的车身并确认问题范围。',
            pinyin:'Qǐng xiān kòuliú shòu yǐngxiǎng de chēshēn bìng quèrèn wèntí fànwéi.',
            english:'Hold the affected bodies first and confirm the scope of the issue.',
            russian:'Сначала удержите затронутые кузова и подтвердите масштаб проблемы.'
          }
        },
        {
          prompt:'Какая проверка процесса наиболее полезна при повторяемом дефекте окраски?',
          options:[
            {label:'Вязкость/материал, распыление, робот, температура/влажность и booth condition', correct:true, consequence:'Проверяются параметры, способные системно влиять на поверхность покрытия.'},
            {label:'Только цвет кузова', correct:false, consequence:'Цвет помогает сегментировать данные, но не заменяет проверку процесса нанесения.'},
            {label:'Только фамилия оператора предыдущей смены', correct:false, consequence:'Персональная привязка без параметров процесса не локализует техническую причину.'}
          ],
          phrase:{
            chinese:'请检查涂料黏度、喷涂参数和喷房环境。',
            pinyin:'Qǐng jiǎnchá túliào niándù, pēntú cānshù hé pēnfáng huánjìng.',
            english:'Check paint viscosity, spray parameters, and booth conditions.',
            russian:'Проверьте вязкость материала, параметры распыления и условия окрасочной камеры.'
          }
        },
        {
          prompt:'Коррекция внесена. Что подтверждает безопасное возвращение процесса?',
          options:[
            {label:'First-off прошёл surface check, rework определён, усиленный контроль назначен', correct:true, consequence:'Исправление подтверждено на продукте, а раннее повторение будет обнаружено.'},
            {label:'Робот снова движется без alarm', correct:false, consequence:'Работоспособность робота не подтверждает качество покрытия.'},
            {label:'Камера прогрета до плановой температуры', correct:false, consequence:'Один параметр не доказывает восстановление всей системы окраски.'}
          ],
          phrase:{
            chinese:'首件表面检查合格后再恢复正常节拍。',
            pinyin:'Shǒujiàn biǎomiàn jiǎnchá hégé hòu zài huīfù zhèngcháng jiépāi.',
            english:'Return to normal takt only after the first-off surface check is OK.',
            russian:'Возвращайтесь к нормальному такту только после успешной проверки поверхности first-off.'
          }
        }
      ]
    },
    safety: {
      title:'Safety Near Miss',
      subtitle:'Stop exposure → isolate/correct → verify before restart.',
      steps:[
        {
          prompt:'Погрузчик пересёк пешеходную зону рядом с работающим постом. Первое действие?',
          options:[
            {label:'Остановить опасное взаимодействие и исключить дальнейшее воздействие', correct:true, consequence:'Экспозиция риска прекращена до разбора причины.'},
            {label:'Сделать фотографию и продолжить работу', correct:false, consequence:'Фиксация полезна, но опасное состояние остаётся активным.'},
            {label:'Предупредить только следующую смену', correct:false, consequence:'Текущая смена продолжает работать с известным риском.'}
          ],
          phrase:{
            chinese:'请立即停止危险作业并隔离风险区域。',
            pinyin:'Qǐng lìjí tíngzhǐ wēixiǎn zuòyè bìng gélí fēngxiǎn qūyù.',
            english:'Stop the unsafe activity immediately and isolate the risk area.',
            russian:'Немедленно остановите опасную работу и изолируйте зону риска.'
          }
        },
        {
          prompt:'Какое действие устраняет причину, а не только симптом?',
          options:[
            {label:'Восстановить разделение потоков, visibility/маркировку и правила движения', correct:true, consequence:'Изменение барьера и стандарта снижает вероятность повторения.'},
            {label:'Попросить всех быть внимательнее', correct:false, consequence:'Призыв к внимательности слабее инженерного или организационного барьера.'},
            {label:'Перенести предупреждающий знак на соседнюю стену', correct:false, consequence:'Косметическое изменение не восстанавливает безопасную организацию потоков.'}
          ],
          phrase:{
            chinese:'请恢复人车分流并确认安全通道。',
            pinyin:'Qǐng huīfù rén chē fēnliú bìng quèrèn ānquán tōngdào.',
            english:'Restore pedestrian-vehicle separation and confirm the safe route.',
            russian:'Восстановите разделение пешеходного и транспортного потоков и подтвердите безопасный маршрут.'
          }
        },
        {
          prompt:'Когда участок можно вернуть в нормальную работу?',
          options:[
            {label:'После проверки барьеров, информирования команды и подтверждения безопасного состояния', correct:true, consequence:'Перезапуск основан на проверенном устранении риска.'},
            {label:'Сразу после освобождения прохода', correct:false, consequence:'Освобождение прохода не подтверждает восстановление системы предотвращения.'},
            {label:'Когда закончится текущая смена', correct:false, consequence:'Время само по себе не устраняет опасное условие.'}
          ],
          phrase:{
            chinese:'确认防护措施有效后才能恢复作业。',
            pinyin:'Quèrèn fánghù cuòshī yǒuxiào hòu cái néng huīfù zuòyè.',
            english:'Work may resume only after the protective measures are verified effective.',
            russian:'Работу можно возобновить только после подтверждения эффективности защитных мер.'
          }
        }
      ]
    },
    engineering: {
      title:'Engineering Change',
      subtitle:'Scope → configuration impact → controlled release and downstream confirmation.',
      steps:[
        {
          prompt:'Поступило изменение компонента от поставщика. Что проверить первым?',
          options:[
            {label:'Affected part/variant, reason, drawing/spec revision and effective point', correct:true, consequence:'Инженер понимает объект изменения и границу его применения.'},
            {label:'Сразу заменить номер в BOM', correct:false, consequence:'Изменение BOM без оценки revision и effective point создаёт конфигурационный риск.'},
            {label:'Передать письмо напрямую на линию', correct:false, consequence:'Неуправляемая информация может попасть в производство до инженерного решения.'}
          ],
          phrase:{
            chinese:'请确认零件版本、变更原因和生效时间点。',
            pinyin:'Qǐng quèrèn língjiàn bǎnběn, biàngēng yuányīn hé shēngxiào shíjiān diǎn.',
            english:'Confirm the part revision, change reason, and effective point.',
            russian:'Подтвердите ревизию детали, причину изменения и точку вступления в силу.'
          }
        },
        {
          prompt:'Какие downstream-объекты нужно оценить до release?',
          options:[
            {label:'BOM, drawing/spec, WI, tooling, quality plan, stock and affected vehicles', correct:true, consequence:'Изменение проверяется по всей цепочке цифрового и физического производства.'},
            {label:'Только CAD-модель', correct:false, consequence:'CAD не отражает все документы, запасы и производственные зависимости.'},
            {label:'Только закупочную цену', correct:false, consequence:'Стоимость важна, но не определяет техническую применимость изменения.'}
          ],
          phrase:{
            chinese:'请评估BOM、图纸、作业指导书和现有库存的影响。',
            pinyin:'Qǐng pínggū BOM, túzhǐ, zuòyè zhǐdǎoshū hé xiànyǒu kùcún de yǐngxiǎng.',
            english:'Assess the impact on BOM, drawings, work instructions, and current stock.',
            russian:'Оцените влияние на BOM, чертежи, рабочие инструкции и текущий запас.'
          }
        },
        {
          prompt:'Что делает engineering change управляемым при запуске?',
          options:[
            {label:'Approved release, serial/effective point, owner, old-stock disposition and first verification', correct:true, consequence:'Конфигурация имеет однозначную границу и проверку первого применения.'},
            {label:'Устная договорённость между инженером и мастером', correct:false, consequence:'Без release и effective point разные функции могут использовать разные версии.'},
            {label:'Удаление старой версии из общей папки', correct:false, consequence:'Удаление файла не заменяет управляемый change record и disposition остатка.'}
          ],
          phrase:{
            chinese:'请确认批准版本、生效点和旧库存处理方案。',
            pinyin:'Qǐng quèrèn pīzhǔn bǎnběn, shēngxiào diǎn hé jiù kùcún chǔlǐ fāng'àn.',
            english:'Confirm the approved revision, effective point, and old-stock disposition.',
            russian:'Подтвердите утверждённую ревизию, точку применения и решение по старому запасу.'
          }
        }
      ]
    },
    supplier: {
      title:'Supplier Escalation',
      subtitle:'Facts → immediate protection → owner, deadline and evidence.',
      steps:[
        {
          prompt:'Китайскому поставщику нужно сообщить о проблеме. Какая первая формулировка лучше?',
          options:[
            {label:'Факт дефекта + part/lot + количество + где обнаружено', correct:true, consequence:'Поставщик получает проверяемую проблему, а не эмоциональную оценку.'},
            {label:'«У вас опять плохое качество»', correct:false, consequence:'Общее обвинение не даёт данных для containment и анализа.'},
            {label:'«Срочно разберитесь» без номера детали', correct:false, consequence:'Без идентификации поставщик не может быстро локализовать продукт и партию.'}
          ],
          phrase:{
            chinese:'我们发现该批次零件存在重复缺陷，请确认批次和数量。',
            pinyin:'Wǒmen fāxiàn gāi pīcì língjiàn cúnzài chóngfù quēxiàn, qǐng quèrèn pīcì hé shùliàng.',
            english:'We found a repeated defect in this lot. Please confirm the lot and quantity.',
            russian:'Мы обнаружили повторяющийся дефект в этой партии. Подтвердите партию и количество.'
          }
        },
        {
          prompt:'Какой запрос защищает производство до готовности root cause?',
          options:[
            {label:'Немедленный containment: stock check, segregation, certified/sorted shipment и ETA', correct:true, consequence:'Производство получает защиту до завершения долгосрочного анализа.'},
            {label:'Только полный 8D через неделю', correct:false, consequence:'Без временного containment завод остаётся под текущим риском.'},
            {label:'Скидка на следующую поставку', correct:false, consequence:'Коммерческая компенсация не защищает качество текущих деталей.'}
          ],
          phrase:{
            chinese:'请立即隔离库存，并提供筛选后合格批次的预计到达时间。',
            pinyin:'Qǐng lìjí gélí kùcún, bìng tígōng shāixuǎn hòu hégé pīcì de yùjì dàodá shíjiān.',
            english:'Please contain the stock immediately and provide the ETA for a certified sorted lot.',
            russian:'Немедленно изолируйте запас и сообщите ETA проверенной отсортированной партии.'
          }
        },
        {
          prompt:'Как завершить эскалацию так, чтобы она была управляемой?',
          options:[
            {label:'Owner + срок containment + срок root cause/action + требуемое доказательство', correct:true, consequence:'Следующие шаги измеримы по владельцу, времени и evidence.'},
            {label:'«Ждём вашего ответа как можно скорее»', correct:false, consequence:'Нет конкретного срока, владельца и критерия завершения.'},
            {label:'Создать большой чат без распределения ответственности', correct:false, consequence:'Количество участников не заменяет owner и decision cadence.'}
          ],
          phrase:{
            chinese:'请确认负责人、临时措施期限、根本原因期限和验证资料。',
            pinyin:'Qǐng quèrèn fùzérén, línshí cuòshī qīxiàn, gēnběn yuányīn qīxiàn hé yànzhèng zīliào.',
            english:'Confirm the owner, containment deadline, root-cause deadline, and verification evidence.',
            russian:'Подтвердите владельца, срок containment, срок root cause и доказательство проверки.'
          }
        }
      ]
    }
  });

  function legacy() { return frontend.get('legacy-app'); }
  function state() { return frontend.get('app-state'); }
  function depth() { return frontend.get('game-depth-v621'); }
  function current() { return state().current(); }
  function query(selector, scope) { return legacy().query(selector, scope); }
  function queryAll(selector, scope) { return legacy().queryAll(selector, scope); }
  function esc(value) { return legacy().escapeHtml(value); }

  function familyFor(scene, gameType) {
    if (gameType === 'dialogue_choice') return 'supplier';
    if (scene === 'paint') return 'paint';
    if (scene === 'welding') return 'welding';
    if (scene === 'logistics' || scene === 'warehouse') return 'logistics';
    if (scene === 'safety') return 'safety';
    if (scene === 'engineering') return 'engineering';
    if (scene === 'meeting') return 'supplier';
    if (scene === 'quality' || scene === 'body' || scene === 'vehicle') return 'quality';
    return 'line_stop';
  }

  function shouldChain(level) {
    return level === 'shift' || level === 'expert';
  }

  function recordFor(key) {
    if (!records.has(key)) {
      records.set(key, {step:0, selection:null, correct:0, risks:[], choices:[], done:false});
      if (records.size > 100) records.delete(records.keys().next().value);
    }
    return records.get(key);
  }

  function phraseMarkup(step) {
    const language = String(current().language || 'chinese');
    if (language === 'chinese') {
      return '<div class="v622-language"><span>Рабочая фраза · 中文</span><b>' + esc(step.phrase.chinese) + '</b>' +
        '<i>' + esc(step.phrase.pinyin) + '</i><small>' + esc(step.phrase.russian) + '</small></div>';
    }
    return '<div class="v622-language"><span>Shop-floor English</span><b>' + esc(step.phrase.english) + '</b>' +
      '<small>' + esc(step.phrase.russian) + '</small></div>';
  }

  function lockStage(stage) {
    stage.classList.add('v622-chain-locked');
    queryAll('button,[role="button"],input,select', stage).forEach(function (node) {
      if (node.closest && node.closest('.v622-chain-panel')) return;
      if (node.dataset.v622Locked === '1') return;
      node.dataset.v622Locked = '1';
      if ('disabled' in node) {
        node.dataset.v622WasDisabled = node.disabled ? '1' : '0';
        node.disabled = true;
      }
      if (node.hasAttribute && node.hasAttribute('tabindex')) node.dataset.v622Tabindex = node.getAttribute('tabindex');
      if (node.setAttribute) {
        node.setAttribute('aria-disabled', 'true');
        if (!('disabled' in node)) node.setAttribute('tabindex', '-1');
      }
    });
  }

  function unlockStage(stage) {
    stage.classList.remove('v622-chain-locked');
    queryAll('[data-v622-locked="1"]', stage).forEach(function (node) {
      if ('disabled' in node) node.disabled = node.dataset.v622WasDisabled === '1';
      if (node.removeAttribute) node.removeAttribute('aria-disabled');
      if (!('disabled' in node)) {
        if (node.dataset.v622Tabindex !== undefined) node.setAttribute('tabindex', node.dataset.v622Tabindex);
        else node.removeAttribute('tabindex');
      }
      delete node.dataset.v622Locked;
      delete node.dataset.v622WasDisabled;
      delete node.dataset.v622Tabindex;
    });
  }

  function stepPanel(chain, record, level) {
    const step = chain.steps[record.step];
    const selected = record.selection;
    const expert = level === 'expert';
    return '<div class="v622-chain-head"><div><span>PRODUCTION DECISION CHAIN</span><h2>' + esc(chain.title) + '</h2><p>' + esc(chain.subtitle) + '</p></div>' +
      '<div class="v622-chain-meter"><b>' + (record.step + 1) + ' / ' + CHAIN_STEPS + '</b><small>' + (expert ? 'EXPERT' : 'SHIFT') + '</small></div></div>' +
      '<div class="v622-chain-track"><i class="done"></i><i class="' + (record.step >= 1 ? 'done' : '') + '"></i><i class="' + (record.step >= 2 ? 'done' : '') + '"></i></div>' +
      '<div class="v622-chain-question"><span>Шаг ' + (record.step + 1) + '</span><h3>' + esc(step.prompt) + '</h3></div>' +
      '<div class="v622-chain-options">' + step.options.map(function (option, index) {
        let cls = '';
        if (selected) cls = index === selected.index ? (selected.correct ? ' selected correct' : ' selected wrong') : ' muted';
        return '<button type="button" data-v622-option="' + index + '" class="' + cls.trim() + '"' + (selected ? ' disabled' : '') + '>' +
          '<b>' + String.fromCharCode(65 + index) + '</b><span>' + esc(option.label) + '</span></button>';
      }).join('') + '</div>' +
      (selected ? '<div class="v622-consequence ' + (selected.correct ? 'good' : 'risk') + '"><b>' + (selected.correct ? 'Решение защищает процесс' : 'Последствие неправильного решения') + '</b><p>' + esc(selected.consequence) + '</p></div>' + phraseMarkup(step) +
        '<div class="v622-chain-actions"><span>Production judgement: <b>' + record.correct + '/' + record.choices.length + '</b> · рисков: <b>' + record.risks.length + '</b></span>' +
        '<button type="button" class="primary" data-v622-next>' + (record.step === CHAIN_STEPS - 1 ? 'Завершить цепочку' : 'Следующий шаг →') + '</button></div>' : '') +
      '<small class="v622-no-xp">Решения этой цепочки развивают производственное мышление и не создают отдельный XP-фарм.</small>';
  }

  function completePanel(chain, record, level) {
    const score = record.correct;
    const status = score === CHAIN_STEPS ? 'Стабильное решение' : score >= 2 ? 'Рабочее решение' : 'Нужно усилить приоритизацию';
    return '<div class="v622-complete"><span>DECISION CHAIN COMPLETE</span><h2>' + esc(status) + '</h2>' +
      '<div class="v622-score"><b>' + score + '<small>/3</small></b><div><strong>' + esc(chain.title) + '</strong><p>Рисковых решений: ' + record.risks.length + '. Теперь открыта основная языковая задача текущего вопроса.</p></div></div>' +
      '<div class="v622-complete-note"><b>' + (level === 'expert' ? 'Экспертный режим' : 'Сменный режим') + '</b><span>Сначала управляем производственным риском, затем решаем языковую задачу.</span></div></div>';
  }

  function bindPanel(panel, stage, chain, record, level) {
    queryAll('[data-v622-option]', panel).forEach(function (button) {
      button.addEventListener('click', function () {
        if (record.selection) return;
        const index = Number(button.dataset.v622Option);
        const option = chain.steps[record.step].options[index];
        const correct = Boolean(option && option.correct);
        record.selection = {index:index, correct:correct, consequence:option ? option.consequence : ''};
        record.choices.push({step:record.step, index:index, correct:correct});
        if (correct) record.correct += 1;
        else record.risks.push({step:record.step, consequence:option ? option.consequence : ''});
        panel.innerHTML = stepPanel(chain, record, level);
        bindPanel(panel, stage, chain, record, level);
      });
    });
    const next = query('[data-v622-next]', panel);
    if (next) next.addEventListener('click', function () {
      if (!record.selection) return;
      if (record.step >= CHAIN_STEPS - 1) {
        record.done = true;
        record.selection = null;
        panel.innerHTML = completePanel(chain, record, level);
        panel.classList.add('complete');
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
    const host = query('.v621-difficulty-panel') || query('.game-lab-summary');
    if (!host || query('.v622-catalog-panel')) return Boolean(host);
    host.insertAdjacentHTML('afterend',
      '<section class="v622-catalog-panel"><div><span>PRODUCTION DECISION CHAINS · v6.0.22</span><h2>На смене важен не один ответ, а порядок действий</h2>' +
      '<p>На уровнях Смена и Эксперт часть языковой практики сначала проходит через три последовательных производственных решения с видимыми последствиями.</p></div>' +
      '<div class="v622-family-list"><span>Andon / Line Stop</span><span>Quality containment</span><span>Supplier delay</span><span>Сварка</span><span>Окраска</span><span>Safety</span><span>Engineering change</span><span>Supplier escalation</span></div></section>');
    return true;
  }

  function decorateSession() {
    const shell = query('.game-session-shell');
    const stage = shell && query('.game-stage', shell);
    const snapshot = current();
    const session = snapshot.gameSessionV618;
    if (!stage || !session || !Array.isArray(session.items)) return false;
    const index = Number(snapshot.gameIndexV618 || 0);
    const item = session.items[index];
    if (!item) return false;
    const level = depth().effectiveDifficulty(index);
    if (!shouldChain(level)) {
      stage.classList.add('v622-training-pass');
      return true;
    }
    const scene = depth().detectScene(session.game_type, item);
    const family = familyFor(scene, session.game_type);
    const chain = CHAINS[family] || CHAINS.line_stop;
    const key = String(session.session_id || session.game_type) + ':' + index + ':' + level + ':' + family;
    const record = recordFor(key);
    let panel = query('.v622-chain-panel', stage);
    if (panel && panel.dataset.v622Key === key) return true;
    if (panel) panel.remove();
    stage.insertAdjacentHTML('afterbegin', '<section class="v622-chain-panel" data-v622-key="' + esc(key) + '"></section>');
    panel = query('.v622-chain-panel', stage);
    if (!panel) return false;
    if (record.done) {
      panel.innerHTML = completePanel(chain, record, level);
      panel.classList.add('complete');
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
    if (String(current().view || '') !== 'games') return;
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
    const main = query('#main');
    if (main && root.MutationObserver) {
      observer = new MutationObserver(scheduleDecorate);
      observer.observe(main, {childList:true, subtree:true});
    }
    document.addEventListener('mgc:state-change', scheduleDecorate);
    document.addEventListener('mgc:frontend-ready', scheduleDecorate);
    scheduleDecorate();
  }

  frontend.register('decision-chains-v622', {
    chains:CHAINS,
    familyFor:familyFor,
    shouldChain:shouldChain,
    decorate:decorate,
    install:install
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
