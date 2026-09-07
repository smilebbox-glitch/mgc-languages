export type Brand = "SHACMAN" | "GWM" | "Отрасль";
export type Market = "Россия" | "Китай" | "Международный";

export type NewsItem = {
  id: string;
  title: string;
  summary: string;
  source: string;
  sourceType: "official" | "media" | "telegram";
  url: string;
  publishedAt: string;
  market: Market;
  brand: Brand;
  originalTitle?: string;
  translated?: boolean;
  live?: boolean;
};

export type AutoEvent = {
  id: string;
  name: string;
  shortName: string;
  category: "Автосалон" | "Компоненты" | "Коммерческий транспорт" | "B2B-форум";
  city: string;
  country: "Китай" | "Россия";
  venue: string;
  start: string;
  end: string;
  url: string;
  source: string;
  latitude: number;
  longitude: number;
  note: string;
  priority: "high" | "normal";
};

export type EventGuidance = {
  whyGo: string;
  access: string;
  ticketPrice: string;
  registrationUrl: string;
};

export type AutoPlace = {
  id: string;
  name: string;
  chineseName: string;
  kind: "Рынок автозапчастей" | "Поставщики";
  city: string;
  address: string;
  description: string;
  latitude: number;
  longitude: number;
  source: string;
};

export const seedNews: NewsItem[] = [
  {
    id: "li-auto-mega-autonomous-strategy-2026-09-02",
    title: "Li Auto делает ставку на минивэны в эпоху автономного вождения",
    summary:
      "Второе поколение Mega подготовлено к уровню L3, получило 710 км запаса хода и вышло в Китае по цене 509,8 тыс. юаней.",
    source: "Китайские автомобили",
    sourceType: "media",
    url: "https://xn----7sbbeeptbfadjdvm5ab9bqj.xn--p1ai/2026/09/02/li-auto-idealnyj-avtomobil/",
    publishedAt: "2026-09-02T23:35:00+03:00",
    market: "Китай",
    brand: "Отрасль",
  },
  {
    id: "li-auto-l9-livis-russia-preorders-2026-09-02",
    title: "В России открыли предзаказы на Li L9 Livis",
    summary:
      "Версия для российского рынка получила разъём CCS2, русифицированное приложение и сервисы «Яндекса»; цена начинается от 12,69 млн рублей.",
    source: "Автопоток",
    sourceType: "telegram",
    url: "https://t.me/autopotoknews/25290",
    publishedAt: "2026-09-02T21:01:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
  {
    id: "moskvich-production-plan-2026-09-02",
    title: "«Москвич» планирует выпустить 20 тысяч автомобилей в 2026 году",
    summary:
      "На новые модели M70 и M90 должно прийтись 5–6 тысяч машин, то есть до 30% годового производственного плана предприятия.",
    source: "Автопоток",
    sourceType: "telegram",
    url: "https://t.me/autopotoknews/25286",
    publishedAt: "2026-09-02T20:22:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
  {
    id: "buryatia-truck-plant-2026-09-02",
    title: "В Бурятии построят завод по выпуску грузовиков",
    summary:
      "Российский и китайский партнёры вложат около 12 млрд рублей в производство дизельной, газовой и электрической техники; полную мощность планируют к 2036 году.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/63023/",
    publishedAt: "2026-09-02T17:01:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
  {
    id: "nio-costs-subscription-2026-09-02",
    title: "Nio прогнозирует рост средней цены автомобиля на 16–17 тыс. юаней",
    summary:
      "Давление сырья и полупроводников повышает себестоимость; часть затрат компания рассчитывает компенсировать подпиской на ассистенты водителя.",
    source: "Китайские автомобили",
    sourceType: "telegram",
    url: "https://t.me/chinamashina_news/15804",
    publishedAt: "2026-09-02T14:02:00+03:00",
    market: "Китай",
    brand: "Отрасль",
  },
  {
    id: "avatr-11-russia-update-2026-09-02",
    title: "Обновлённый Avatr 11 представлен для российского рынка",
    summary:
      "Модель получила новый декор и ароматизацию салона, сохранив стартовую цену 6,99 млн рублей.",
    source: "Автопоток",
    sourceType: "telegram",
    url: "https://t.me/autopotoknews/25261",
    publishedAt: "2026-09-02T14:20:00+03:00",
    market: "Россия",
    brand: "Отрасль",
  },
  {
    id: "gwm-pickup-market-russia-2026-09-02",
    title: "GWM вошёл в пятёрку лидеров российского рынка пикапов",
    summary:
      "В июле бренд реализовал 318 новых пикапов; сегмент вырос на 19%, а первое место впервые занял Foton.",
    source: "АВТОСТАТ",
    sourceType: "telegram",
    url: "https://t.me/autostatis/22610",
    publishedAt: "2026-09-02T07:01:00+03:00",
    market: "Россия",
    brand: "GWM",
  },
  {
    id: "china-overseas-guidelines-2026-09-01",
    title: "Китай обновил правила для зарубежной работы автопроизводителей",
    summary:
      "Новые рекомендации усиливают требования к комплаенсу, ценообразованию, локальным стандартам и управлению рисками на внешних рынках.",
    source: "Reuters",
    sourceType: "media",
    url: "https://www.reuters.com/world/asia-pacific/china-issues-overseas-compliance-rules-automakers-warns-against-disruptive-2026-09-01/",
    publishedAt: "2026-09-01T09:00:00+08:00",
    market: "Китай",
    brand: "Отрасль",
  },
  {
    id: "shacman-eurasia-expo-2026-07-01",
    title: "SHACMAN показал решения всей производственной цепочки на China-Eurasia Expo",
    originalTitle: "陕汽携全产业链硬核成果亮相第九届中国—亚欧博览会",
    summary:
      "Shaanxi Automobile представил технику и решения группы на девятой выставке China-Eurasia Expo. Материал переведён с официального китайского источника.",
    source: "Shaanxi Automobile",
    sourceType: "official",
    url: "https://www.sxqc.com/news/news-detail-156560.htm",
    publishedAt: "2026-07-01T10:00:00+08:00",
    market: "Китай",
    brand: "SHACMAN",
    translated: true,
  },
  {
    id: "gwm-poer-manual-russia-2026-07-01",
    title: "В России начались продажи GWM Poer с механической коробкой передач",
    summary:
      "Версию «Комфорт» предложили с бензиновым и дизельным двигателями, полным приводом Part-Time и грузоподъёмностью до 975 кг.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62636/",
    publishedAt: "2026-07-01T09:49:00+03:00",
    market: "Россия",
    brand: "GWM",
  },
  {
    id: "shacman-gas-6000-delivery-2026-06-24",
    title: "SHACMAN передал заказчику партию газовых грузовиков серии 6000",
    originalTitle: "陕汽重卡6000系列燃气车批量交付快递快运客户",
    summary:
      "Официальный материал посвящён серийной поставке газовых тяжёлых грузовиков клиенту из сегмента экспресс-доставки и магистральных перевозок.",
    source: "Shaanxi Automobile",
    sourceType: "official",
    url: "https://www.sxqc.com/news/news-detail-155710.htm",
    publishedAt: "2026-06-24T10:00:00+08:00",
    market: "Китай",
    brand: "SHACMAN",
    translated: true,
  },
  {
    id: "gwm-russia-president-2026-06-18",
    title: "Лю Яцзе возглавил «Грейт Волл Мотор Рус»",
    summary:
      "Новому президенту российского офиса поручено укрепление позиций концерна, расширение модельного ряда и развитие дилерской сети.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62563/",
    publishedAt: "2026-06-18T13:27:00+03:00",
    market: "Россия",
    brand: "GWM",
  },
  {
    id: "gwm-transmission-localization-2026-06-08",
    title: "GWM готовит в России производство автоматических коробок передач",
    summary:
      "Проект в Тульской области должен углубить локализацию агрегатов Haval; параллельно предприятие переходит на экологический стандарт Евро-6.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62503/",
    publishedAt: "2026-06-08T09:52:00+03:00",
    market: "Россия",
    brand: "GWM",
  },
  {
    id: "shacman-russia-strategy-2026-05-27",
    title: "SHACMAN представил обновлённую стратегию развития в России",
    summary:
      "На COMvex 2026 бренд обозначил долгосрочный план работы на российском рынке и показал обновлённые модели коммерческой техники.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62437/",
    publishedAt: "2026-05-27T12:00:00+03:00",
    market: "Россия",
    brand: "SHACMAN",
  },
  {
    id: "gwm-security-russia-2026-05-21",
    title: "Great Wall Motor запустил сервис «GWM Безопасность»",
    summary:
      "Телематический сервис для Haval, TANK и WEY включает мониторинг тревожных событий, помощь при ДТП и противоугонные функции.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62384/",
    publishedAt: "2026-05-21T09:32:00+03:00",
    market: "Россия",
    brand: "GWM",
  },
  {
    id: "shacman-recall-russia-2026-04-13",
    title: "В России объявили отзыв 2 116 грузовиков SHACMAN SX3258",
    summary:
      "Кампания касается проверки и устранения выявленного несоответствия у части автомобилей, представленных на российском рынке.",
    source: "АВТОСТАТ",
    sourceType: "media",
    url: "https://www.autostat.ru/news/62163/",
    publishedAt: "2026-04-13T10:00:00+03:00",
    market: "Россия",
    brand: "SHACMAN",
  },
  {
    id: "gwm-sales-record-2026-01-01",
    title: "Продажи Great Wall Motor в 2025 году достигли рекордных 1,3237 млн автомобилей",
    originalTitle: "创历史新高！长城汽车2025年销售新车132.37万辆，同比增长7.33%",
    summary:
      "Официальный отчёт GWM сообщает о росте годовых продаж на 7,33%. Заголовок и ключевые показатели переведены с китайского.",
    source: "Great Wall Motor",
    sourceType: "official",
    url: "https://www.gwm.com.cn/news/3403845.html",
    publishedAt: "2026-01-01T09:00:00+08:00",
    market: "Китай",
    brand: "GWM",
    translated: true,
  },
];

export const autoEvents: AutoEvent[] = [
  {
    id: "citexpo-2026",
    name: "China International Tire & Wheel Technology Expo 2026",
    shortName: "CITEXPO",
    category: "Компоненты",
    city: "Шанхай",
    country: "Китай",
    venue: "Shanghai World Expo Exhibition & Convention Center",
    start: "2026-09-02",
    end: "2026-09-04",
    url: "https://en.citwtexpo.com/",
    source: "Организатор CITEXPO",
    latitude: 31.1812,
    longitude: 121.4894,
    note: "Шины, колёса, материалы, оборудование и поставщики aftermarket.",
    priority: "high",
  },
  {
    id: "china-nev-icv-2026",
    name: "China International New Energy and Intelligent Connected Vehicle Exhibition",
    shortName: "NEV & ICV China",
    category: "Компоненты",
    city: "Пекин",
    country: "Китай",
    venue: "China International Exhibition Center",
    start: "2026-10-21",
    end: "2026-10-24",
    url: "https://www.expofinder.com/en/detail/q2WlK24G?from=organizer",
    source: "ExpoFinder",
    latitude: 40.072,
    longitude: 116.555,
    note: "Новая энергетика, интеллектуальный транспорт, электроника и цепочка поставок.",
    priority: "normal",
  },
  {
    id: "bauma-china-2026",
    name: "bauma CHINA 2026",
    shortName: "bauma CHINA",
    category: "Коммерческий транспорт",
    city: "Шанхай",
    country: "Китай",
    venue: "SNIEC + SWEECC",
    start: "2026-11-23",
    end: "2026-11-27",
    url: "https://bauma-china.com/en/",
    source: "Messe München",
    latitude: 31.2088,
    longitude: 121.5633,
    note: "Строительная техника, карьерные машины, спецтранспорт и поставщики тяжёлого машиностроения.",
    priority: "high",
  },
  {
    id: "auto-tech-guangzhou-2026",
    name: "Guangzhou Automotive Technology Expo 2026",
    shortName: "AUTO TECH China",
    category: "Компоненты",
    city: "Гуанчжоу",
    country: "Китай",
    venue: "China Import & Export Fair Complex, Area D",
    start: "2026-11-27",
    end: "2026-11-30",
    url: "https://www.china-autotech.com/english",
    source: "AUTO TECH China",
    latitude: 23.104,
    longitude: 113.3667,
    note: "Электроника, ПО, шасси, smart cockpit, испытания и технологии производства.",
    priority: "high",
  },
  {
    id: "auto-guangzhou-2026",
    name: "24th Guangzhou International Automobile Exhibition",
    shortName: "Auto Guangzhou",
    category: "Автосалон",
    city: "Гуанчжоу",
    country: "Китай",
    venue: "Canton Fair Complex",
    start: "2026-11-27",
    end: "2026-12-06",
    url: "https://www.adsale.com.hk/autoguangzhou/",
    source: "Организатор Auto Guangzhou",
    latitude: 23.104,
    longitude: 113.3667,
    note: "Автомобили и новинки брендов; B2B-зона цепочки поставок работает 27-30 ноября.",
    priority: "high",
  },
  {
    id: "automechanika-shanghai-2026",
    name: "Automechanika Shanghai 2026",
    shortName: "Automechanika",
    category: "Компоненты",
    city: "Шанхай",
    country: "Китай",
    venue: "National Exhibition and Convention Center",
    start: "2026-12-02",
    end: "2026-12-05",
    url: "https://automechanika-shanghai.hk.messefrankfurt.com/shanghai/en.html",
    source: "Messe Frankfurt",
    latitude: 31.1903,
    longitude: 121.299,
    note: "Крупнейшая площадка по компонентам, оборудованию, сервису и автомобильным технологиям.",
    priority: "high",
  },
  {
    id: "capas-chengdu-2027",
    name: "Chengdu International Trade Fair for Automotive Parts and Aftermarket Services",
    shortName: "CAPAS Chengdu",
    category: "Компоненты",
    city: "Чэнду",
    country: "Китай",
    venue: "Chengdu Century City New International Exhibition & Convention Center",
    start: "2027-05-20",
    end: "2027-05-22",
    url: "https://capas-chengdu.hk.messefrankfurt.com/chengdu/en.html",
    source: "Messe Frankfurt",
    latitude: 30.559,
    longitude: 104.068,
    note: "Автокомпоненты, коммерческий транспорт, aftermarket и интеллектуальная мобильность.",
    priority: "normal",
  },
  {
    id: "chengdu-motor-show-2026",
    name: "29th Chengdu International Motor Show",
    shortName: "Chengdu Motor Show",
    category: "Автосалон",
    city: "Чэнду",
    country: "Китай",
    venue: "Western China International Expo City",
    start: "2026-08-21",
    end: "2026-08-30",
    url: "https://www.hmf-china.com/En/Events/Information/?CID=16&EID=46",
    source: "Hannover Milano Fairs Shanghai",
    latitude: 30.418,
    longitude: 104.078,
    note: "Архив: автосалон Западного Китая, автомобили, компоненты и aftermarket.",
    priority: "normal",
  },
  {
    id: "capas-chengdu-2026",
    name: "CAPAS Chengdu 2026",
    shortName: "CAPAS Chengdu",
    category: "Компоненты",
    city: "Чэнду",
    country: "Китай",
    venue: "Chengdu Century City New International Exhibition & Convention Center",
    start: "2026-05-21",
    end: "2026-05-23",
    url: "https://capas-chengdu.hk.messefrankfurt.com/chengdu/en/press.html",
    source: "Messe Frankfurt",
    latitude: 30.559,
    longitude: 104.068,
    note: "Архив: компоненты, коммерческие автомобили и услуги aftermarket.",
    priority: "normal",
  },
  {
    id: "auto-china-2026",
    name: "Beijing International Automotive Exhibition 2026",
    shortName: "Auto China",
    category: "Автосалон",
    city: "Пекин",
    country: "Китай",
    venue: "New China International Exhibition Centre",
    start: "2026-04-24",
    end: "2026-05-03",
    url: "https://www.adsale.com.hk/AutoChina/AUTO/idx/eng",
    source: "Организатор Auto China",
    latitude: 40.072,
    longitude: 116.555,
    note: "Архив: ключевой международный автосалон Китая.",
    priority: "normal",
  },
];

export const eventGuidance: Record<string, EventGuidance> = {
  "citexpo-2026": {
    whyGo: "Подходит для прямого поиска шин, дисков, сырья, оборудования и контрактных партнёров из Китая.",
    access: "Заполнить анкету профессионального посетителя на сайте организатора. Для выдачи бейджа могут запросить данные компании и удостоверение личности.",
    ticketPrice: "Бесплатно для подтверждённых отраслевых специалистов по предварительной регистрации.",
    registrationUrl: "https://www.citexpo.com.cn/en/visitor/register_form.php",
  },
  "china-nev-icv-2026": {
    whyGo: "Полезно для оценки китайской политики по NEV, автономному вождению, зарядной инфраструктуре и поиска технологических партнёров.",
    access: "Нужна предварительная регистрация посетителя. Возьмите паспорт: на крупных выставках Китая действует именной контроль доступа.",
    ticketPrice: "Цена организатором пока не опубликована; требуется регистрация.",
    registrationUrl: "https://en.jufair.com/ticket/13936.html",
  },
  "bauma-china-2026": {
    whyGo: "Главная поездка для SHACMAN и тяжёлой техники: карьерные машины, строительный транспорт, силовые установки и поставщики комплектующих.",
    access: "Зарегистрироваться онлайн до 21 ноября и получить QR-код. На входе нужен оригинал паспорта; один бейдж действует на обе площадки.",
    ticketPrice: "Бесплатно до 21 ноября; после этой даты — 80 CNY (примерно 960 ₽) за человека.",
    registrationUrl: "https://bauma-china.com/en/trade-fair/tickets/",
  },
  "auto-tech-guangzhou-2026": {
    whyGo: "Для инженеров и закупок: электроника, ПО, шасси, smart cockpit, испытания, термоменеджмент и поставщики Tier-1/Tier-2.",
    access: "Подать заявку профессионального посетителя через Visitor Center; для групп доступна отдельная регистрация у организатора.",
    ticketPrice: "Стоимость посещения 2026 пока не опубликована; регистрация обязательна.",
    registrationUrl: "https://www.china-autotech.com/english",
  },
  "auto-guangzhou-2026": {
    whyGo: "Нужно ехать за новыми моделями GWM и конкурентов, переговорами с OEM и поставщиками, а также оценкой трендов Южного Китая.",
    access: "Для B2B-дней пройти предварительную регистрацию trade visitor. Публичные билеты обычно продаются через официальный WeChat выставки.",
    ticketPrice: "Тариф 2026 ещё не опубликован. Ориентир 2025: 100 CNY (примерно 1 200 ₽) в профессиональный день и 50 CNY (примерно 600 ₽) в публичный день.",
    registrationUrl: "https://www.adsale.com.hk/AutoGZ/Web/visitor-preregistration/register/eng",
  },
  "automechanika-shanghai-2026": {
    whyGo: "Ключевая площадка для компонентов, aftermarket, оборудования и сервиса; есть деловой matching с поставщиками и покупателями.",
    access: "Предварительно зарегистрироваться, получить QR-код и обменять его на бейдж по оригиналу паспорта. Допуск только для специалистов 18+.",
    ticketPrice: "Бесплатно для профессиональных посетителей 18+.",
    registrationUrl: "https://automechanika-shanghai.hk.messefrankfurt.com/shanghai/en/planning-preparation/visitors.html",
  },
  "capas-chengdu-2027": {
    whyGo: "Подходит для выхода на рынок Западного Китая: компоненты, коммерческий транспорт, aftermarket, электрификация и региональные дистрибьюторы.",
    access: "Оформить visitor registration на сайте Messe Frankfurt; зарубежным посетителям заранее подготовить паспортные данные и визовые документы.",
    ticketPrice: "Цена 2027 пока не опубликована; организатор откроет регистрацию ближе к выставке.",
    registrationUrl: "https://capas-chengdu.hk.messefrankfurt.com/chengdu/en/planning-preparation.html",
  },
  "chengdu-motor-show-2026": {
    whyGo: "Архивный ориентир по спросу и продуктовым трендам Западного Китая, особенно по SUV, пикапам и новым энергетическим автомобилям.",
    access: "Выставка завершена; использовать официальный сайт для итогов, списка участников и планирования следующего выпуска.",
    ticketPrice: "Событие завершено; билеты больше не продаются.",
    registrationUrl: "https://www.hmf-china.com/En/Events/Information/?CID=16&EID=46",
  },
  "capas-chengdu-2026": {
    whyGo: "Архив для поиска участников рынка компонентов, коммерческого транспорта и aftermarket Юго-Западного Китая.",
    access: "Выставка завершена; на сайте организатора доступны итоги и контакты для CAPAS Chengdu 2027.",
    ticketPrice: "Событие завершено; билеты больше не продаются.",
    registrationUrl: "https://capas-chengdu.hk.messefrankfurt.com/chengdu/en.html",
  },
  "auto-china-2026": {
    whyGo: "Архив ключевого автосалона Китая: мировые премьеры, NEV, интеллектуальное вождение, компоненты и стратегии крупнейших OEM.",
    access: "Выставка завершена; официальный сайт сохраняет программу, планы павильонов и информацию для подготовки к следующему Auto China.",
    ticketPrice: "Событие завершено; билеты больше не продаются.",
    registrationUrl: "https://www.beijingautoshow.com/visitors/",
  },
};

export const autoPlaces: AutoPlace[] = [
  {
    id: "guangyuan-zhiyou",
    name: "Guangyuan Zhiyou Automobile Parts City",
    chineseName: "广州广园致友汽配城",
    kind: "Рынок автозапчастей",
    city: "Гуанчжоу",
    address: "1540 Guangyuan East Road, Guangzhou, Guangdong",
    description: "Крупный оптовый кластер автомобильных деталей, расходников и аксессуаров.",
    latitude: 23.1604,
    longitude: 113.2907,
    source: "BigChina BusinessBoard.pdf",
  },
  {
    id: "yongfu-auto-supplies",
    name: "Yongfu International Auto Supplies City",
    chineseName: "广东永福国际汽车用品城",
    kind: "Рынок автозапчастей",
    city: "Гуанчжоу",
    address: "48 Yongfu Road, Guangzhou, Guangdong",
    description: "Оптовый рынок автозапчастей, автоаксессуаров, электроники и товаров для сервиса.",
    latitude: 23.1447,
    longitude: 113.297,
    source: "BigChina BusinessBoard.pdf",
  },
  {
    id: "linyi-fittings-town",
    name: "Linyi Car & Motorcycle Fittings Town",
    chineseName: "临沂汽摩配城",
    kind: "Поставщики",
    city: "Линьи",
    address: "Gongye Avenue, Lanshan District, Linyi, Shandong",
    description: "Запчасти для автомобилей, мото- и сельхозтехники, масла, шины и автоаксессуары.",
    latitude: 35.087,
    longitude: 118.279,
    source: "BigChina BusinessBoard.pdf",
  },
];

export const sourceChannels = [
  { name: "Русский автомобиль etc", handle: "rusautomobile2", kind: "Telegram" },
  { name: "Китайские автомобили: новости", handle: "chinamashina_news", kind: "Telegram" },
  { name: "Автопоток", handle: "autopotoknews", kind: "Telegram" },
  { name: "Китайские автомобили", handle: "chinamashina", kind: "Telegram" },
  { name: "China Cars", handle: "ChinaCars774", kind: "Telegram" },
  { name: "АВТОСТАТ: статистика", handle: "autostatis", kind: "Telegram" },
];

export const sourceWebsites = [
  { name: "Shaanxi Automobile", url: "https://www.sxqc.com/", market: "Китай" as const, language: "zh" as const },
  { name: "АВТОСТАТ", url: "https://www.autostat.ru/", market: "Россия" as const, language: "ru" as const },
  { name: "Китайские автомобили", url: "https://xn----7sbbeeptbfadjdvm5ab9bqj.xn--p1ai/?tgm", market: "Россия" as const, language: "ru" as const },
  { name: "人民网汽车", url: "https://auto.people.com.cn/", market: "Китай" as const, language: "zh" as const },
  { name: "新华网汽车", url: "https://www.xinhuanet.com/auto/", market: "Китай" as const, language: "zh" as const },
  { name: "央视网汽车", url: "https://auto.cctv.com/", market: "Китай" as const, language: "zh" as const },
  { name: "汽车之家", url: "https://www.autohome.com.cn/", market: "Китай" as const, language: "zh" as const },
  { name: "易车", url: "https://www.yiche.com/", market: "Китай" as const, language: "zh" as const },
  { name: "太平洋汽车", url: "https://www.pcauto.com.cn/", market: "Китай" as const, language: "zh" as const },
];
