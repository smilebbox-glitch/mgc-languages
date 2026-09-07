export type HotelOption = {
  name: string;
  chineseName: string;
  proximity: string;
  nightlyPrice: string;
  bookingUrl: string;
};

export type Attraction = {
  name: string;
  chineseName: string;
  addressZh: string;
  note: string;
  mapUrl: string;
  wikipediaUrl: string;
};

export type EventTravelPlan = {
  travelWindow: string;
  nights: number;
  flightPrice: string;
  flightUrl: string;
  journeyFromSvo: string;
  journeyBreakdown: string;
  stayBudget: string;
  hotels: HotelOption[];
  attractions: Attraction[];
};

export type UnionPayOption = {
  bank: string;
  status: string;
  howToOpen: string;
  cost: string;
  url: string;
};

export const unionPayOptions: UnionPayOption[] = [
  {
    bank: "Россельхозбанк",
    status: "Рублёвая и валютная UnionPay",
    howToOpen: "Подать заявку онлайн или в офисе; пластик получить до поездки и заранее проверить оплату и снятие наличных.",
    cost: "Рублёвый выпуск может быть бесплатным по акции; валютная карта — по действующему тарифу банка.",
    url: "https://www.rshb.ru/natural/debetcards/unionpay-china",
  },
  {
    bank: "Азиатско-Тихоокеанский Банк",
    status: "UnionPay в рублях или юанях",
    howToOpen: "Обратиться в отделение с паспортом; наличие моментальной и именной карты уточнить перед визитом.",
    cost: "Выпуск и обслуживание зависят от валюты и пакета; банк может обнулить обслуживание при выполнении условий.",
    url: "https://www.atb.su/",
  },
  {
    bank: "Центр-инвест",
    status: "Международная карта UnionPay",
    howToOpen: "Заполнить анкету на сайте или через Госуслуги и выбрать офис получения.",
    cost: "Обслуживание — 0 ₽ при выполнении условий, иначе 299 ₽ в месяц.",
    url: "https://www.centrinvest.ru/for-individuals/cards",
  },
  {
    bank: "Инго Банк",
    status: "UnionPay со счётом в рублях или юанях",
    howToOpen: "Стать клиентом банка, затем заказать карту на сайте или в приложении; доступна доставка.",
    cost: "Выпуск — 3 000 ₽ или 450 CNY; обслуживание заявлено бесплатным.",
    url: "https://ingobank.ru/news/ingo-bank-nachal-vypusk-kart-unionpay-/",
  },
];

export const tripDocuments = [
  "Оригинал загранпаспорта; разумный запас срока действия — не менее 6 месяцев после поездки.",
  "Обратный билет, подтверждение проживания и медицинская страховка на весь срок.",
  "Регистрация на выставку, QR-код или приглашение и визитки компании.",
  "Для поездок после 14 сентября 2026 года — виза КНР либо официальное подтверждение продления безвизового режима.",
];

const shanghaiExpoHotels: HotelOption[] = [
  {
    name: "InterContinental Shanghai Expo",
    chineseName: "上海世博洲际酒店",
    proximity: "рядом с World Expo Exhibition Center",
    nightlyPrice: "9 000–17 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=InterContinental%20Shanghai%20Expo",
  },
  {
    name: "Holiday Inn Express Shanghai Expo Centre",
    chineseName: "上海世博中心智选假日酒店",
    proximity: "короткая поездка до площадки",
    nightlyPrice: "5 000–9 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=Holiday%20Inn%20Express%20Shanghai%20Expo%20Centre",
  },
];

const shanghaiPudongHotels: HotelOption[] = [
  {
    name: "Kerry Hotel Pudong Shanghai",
    chineseName: "上海浦东嘉里大酒店",
    proximity: "соединён переходом со SNIEC",
    nightlyPrice: "12 000–22 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=Kerry%20Hotel%20Pudong%20Shanghai",
  },
  {
    name: "Dorsett Shanghai",
    chineseName: "上海帝盛酒店",
    proximity: "около 10 минут на такси до SNIEC",
    nightlyPrice: "6 500–11 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=Dorsett%20Shanghai",
  },
];

const shanghaiHongqiaoHotels: HotelOption[] = [
  {
    name: "Primus Hotel Shanghai Hongqiao",
    chineseName: "上海虹桥绿地铂瑞酒店",
    proximity: "рядом с NECC",
    nightlyPrice: "7 000–13 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=Primus%20Hotel%20Shanghai%20Hongqiao",
  },
  {
    name: "InterContinental Shanghai Hongqiao NECC",
    chineseName: "上海国家会展中心洲际酒店",
    proximity: "пешком до павильонов NECC",
    nightlyPrice: "10 000–18 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=2&searchWord=InterContinental%20Shanghai%20Hongqiao%20NECC",
  },
];

const beijingHotels: HotelOption[] = [
  {
    name: "Crowne Plaza Beijing International Airport",
    chineseName: "北京临空皇冠假日酒店",
    proximity: "район аэропорта и CIEC Shunyi",
    nightlyPrice: "7 000–13 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=1&searchWord=Crowne%20Plaza%20Beijing%20International%20Airport",
  },
  {
    name: "CITIC Hotel Beijing Airport",
    chineseName: "北京国都大饭店",
    proximity: "короткая поездка до выставочного центра",
    nightlyPrice: "5 000–9 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=1&searchWord=CITIC%20Hotel%20Beijing%20Airport",
  },
];

const guangzhouHotels: HotelOption[] = [
  {
    name: "Langham Place Guangzhou",
    chineseName: "广州南丰朗豪酒店",
    proximity: "напротив комплекса Canton Fair",
    nightlyPrice: "10 000–18 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=32&searchWord=Langham%20Place%20Guangzhou",
  },
  {
    name: "The Westin Pazhou",
    chineseName: "广州广交会威斯汀酒店",
    proximity: "соединён с выставочным комплексом",
    nightlyPrice: "9 000–16 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=32&searchWord=The%20Westin%20Pazhou",
  },
];

const chengduHotels: HotelOption[] = [
  {
    name: "InterContinental Century City Chengdu",
    chineseName: "成都世纪城天堂洲际大饭店",
    proximity: "рядом с Century City выставочным центром",
    nightlyPrice: "7 000–13 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=28&searchWord=InterContinental%20Century%20City%20Chengdu",
  },
  {
    name: "Holiday Inn Chengdu Century City",
    chineseName: "成都世纪城假日酒店",
    proximity: "пешком до площадки",
    nightlyPrice: "4 500–8 000 ₽ / ночь",
    bookingUrl: "https://www.trip.com/hotels/list?city=28&searchWord=Holiday%20Inn%20Chengdu%20Century%20City",
  },
];

const shanghaiAttractions: Attraction[] = [
  {
    name: "Набережная Вайтань",
    chineseName: "外滩",
    addressZh: "上海市黄浦区中山东一路",
    note: "Панорама Пудуна и историческая архитектура; лучше после заката.",
    mapUrl: "https://map.baidu.com/search/上海市黄浦区中山东一路",
    wikipediaUrl: "https://en.wikipedia.org/wiki/The_Bund",
  },
  {
    name: "Сад Юй",
    chineseName: "豫园",
    addressZh: "上海市黄浦区福佑路168号",
    note: "Классический китайский сад и старый торговый квартал.",
    mapUrl: "https://map.baidu.com/search/上海市黄浦区福佑路168号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Yu_Garden",
  },
  {
    name: "Шанхайская башня",
    chineseName: "上海中心大厦",
    addressZh: "上海市浦东新区陆家嘴环路479号",
    note: "Смотровая площадка в деловом районе Лудзяцзуй.",
    mapUrl: "https://map.baidu.com/search/上海市浦东新区陆家嘴环路479号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Shanghai_Tower",
  },
];

const beijingAttractions: Attraction[] = [
  {
    name: "Запретный город",
    chineseName: "故宫博物院",
    addressZh: "北京市东城区景山前街4号",
    note: "Главный исторический комплекс столицы; слот лучше бронировать заранее.",
    mapUrl: "https://map.baidu.com/search/北京市东城区景山前街4号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Forbidden_City",
  },
  {
    name: "Храм Неба",
    chineseName: "天坛公园",
    addressZh: "北京市东城区天坛东里甲1号",
    note: "Императорский храмовый парк и удобная прогулка на 2–3 часа.",
    mapUrl: "https://map.baidu.com/search/北京市东城区天坛东里甲1号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Temple_of_Heaven",
  },
];

const guangzhouAttractions: Attraction[] = [
  {
    name: "Кантонская башня",
    chineseName: "广州塔",
    addressZh: "广州市海珠区阅江西路222号",
    note: "Панорама города рядом с выставочным районом Пачжоу.",
    mapUrl: "https://map.baidu.com/search/广州市海珠区阅江西路222号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Canton_Tower",
  },
  {
    name: "Академия клана Чэнь",
    chineseName: "陈家祠",
    addressZh: "广州市荔湾区中山七路恩龙里34号",
    note: "Архитектура и декоративное искусство провинции Гуандун.",
    mapUrl: "https://map.baidu.com/search/广州市荔湾区中山七路恩龙里34号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Chen_Clan_Ancestral_Hall",
  },
];

const chengduAttractions: Attraction[] = [
  {
    name: "Исследовательская база панд",
    chineseName: "成都大熊猫繁育研究基地",
    addressZh: "成都市成华区熊猫大道1375号",
    note: "Приезжать лучше к открытию, когда панды наиболее активны.",
    mapUrl: "https://map.baidu.com/search/成都市成华区熊猫大道1375号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Chengdu_Research_Base_of_Giant_Panda_Breeding",
  },
  {
    name: "Храм Ухоу",
    chineseName: "成都武侯祠",
    addressZh: "成都市武侯区武侯祠大街231号",
    note: "История эпохи Троецарствия и традиционная архитектура.",
    mapUrl: "https://map.baidu.com/search/成都市武侯区武侯祠大街231号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Wuhou%2C_Chengdu",
  },
  {
    name: "Аллеи Куаньчжай",
    chineseName: "宽窄巷子",
    addressZh: "成都市青羊区长顺上街127号",
    note: "Исторические улицы, сычуаньская кухня и чайные дома.",
    mapUrl: "https://map.baidu.com/search/成都市青羊区长顺上街127号",
    wikipediaUrl: "https://en.wikipedia.org/wiki/Kuanzhaixiangzi_Alleys_station",
  },
];

export const eventTravelPlans: Record<string, EventTravelPlan> = {
  "citexpo-2026": {
    travelWindow: "1–5 сентября 2026",
    nights: 4,
    flightPrice: "55 000–95 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/sha",
    journeyFromSvo: "примерно 13–14,5 часов",
    journeyBreakdown: "2,5 часа до вылета + 8 ч 50 мин прямой рейс + 1–1,5 часа на границу и багаж + 45–60 минут до SWEECC.",
    stayBudget: "20 000–68 000 ₽ за 4 ночи",
    hotels: shanghaiExpoHotels,
    attractions: shanghaiAttractions,
  },
  "china-nev-icv-2026": {
    travelWindow: "20–25 октября 2026",
    nights: 5,
    flightPrice: "45 000–75 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/bjs",
    journeyFromSvo: "примерно 11,5–13 часов",
    journeyBreakdown: "2,5 часа до вылета + 7 ч 45 мин прямой рейс + 1–1,5 часа на границу и багаж + 20–30 минут до CIEC Shunyi.",
    stayBudget: "25 000–65 000 ₽ за 5 ночей",
    hotels: beijingHotels,
    attractions: beijingAttractions,
  },
  "bauma-china-2026": {
    travelWindow: "22–28 ноября 2026",
    nights: 6,
    flightPrice: "50 000–85 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/sha",
    journeyFromSvo: "примерно 12,5–14 часов",
    journeyBreakdown: "2,5 часа до вылета + 8 ч 50 мин прямой рейс + 1–1,5 часа на границу и багаж + около 35–60 минут до SNIEC.",
    stayBudget: "39 000–132 000 ₽ за 6 ночей",
    hotels: shanghaiPudongHotels,
    attractions: shanghaiAttractions,
  },
  "auto-tech-guangzhou-2026": {
    travelWindow: "26 ноября — 1 декабря 2026",
    nights: 5,
    flightPrice: "50 000–85 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/can",
    journeyFromSvo: "примерно 13,5–15 часов",
    journeyBreakdown: "2,5 часа до вылета + 9 ч 15 мин прямой рейс + 1–1,5 часа на границу и багаж + 55–80 минут до комплекса Canton Fair.",
    stayBudget: "45 000–90 000 ₽ за 5 ночей",
    hotels: guangzhouHotels,
    attractions: guangzhouAttractions,
  },
  "auto-guangzhou-2026": {
    travelWindow: "26 ноября — 1 декабря для B2B или до 7 декабря для полного салона",
    nights: 5,
    flightPrice: "50 000–85 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/can",
    journeyFromSvo: "примерно 13,5–15 часов",
    journeyBreakdown: "2,5 часа до вылета + 9 ч 15 мин прямой рейс + 1–1,5 часа на границу и багаж + 55–80 минут до комплекса Canton Fair.",
    stayBudget: "45 000–90 000 ₽ за 5 ночей; полный салон — до 198 000 ₽",
    hotels: guangzhouHotels,
    attractions: guangzhouAttractions,
  },
  "automechanika-shanghai-2026": {
    travelWindow: "1–6 декабря 2026",
    nights: 5,
    flightPrice: "50 000–85 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/sha",
    journeyFromSvo: "примерно 13,5–15 часов",
    journeyBreakdown: "2,5 часа до вылета + 8 ч 50 мин прямой рейс + 1–1,5 часа на границу и багаж + 50–80 минут до NECC Hongqiao.",
    stayBudget: "35 000–90 000 ₽ за 5 ночей",
    hotels: shanghaiHongqiaoHotels,
    attractions: shanghaiAttractions,
  },
  "capas-chengdu-2027": {
    travelWindow: "19–23 мая 2027",
    nights: 4,
    flightPrice: "50 000–85 000 ₽ туда-обратно",
    flightUrl: "https://www.aviasales.ru/routes/mow/ctu",
    journeyFromSvo: "примерно 12–13,5 часов",
    journeyBreakdown: "2,5 часа до вылета + 7 ч 40 мин прямой рейс + 1–1,5 часа на границу и багаж + около 50 минут от TFU до Century City.",
    stayBudget: "18 000–52 000 ₽ за 4 ночи",
    hotels: chengduHotels,
    attractions: chengduAttractions,
  },
};

export const travelPriceNotice =
  "Цены — ориентир для 1 человека из Москвы в экономклассе. Время пути рассчитано от прибытия в Шереметьево до площадки при прямом рейсе; пересадка, очередь на границе и пробки увеличат его. Откройте ссылки и выберите точные даты перед согласованием поездки.";
