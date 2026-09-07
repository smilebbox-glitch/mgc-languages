import {
  ArrowUpRight,
  BatteryCharging,
  BriefcaseBusiness,
  Camera,
  CarFront,
  CircleAlert,
  CreditCard,
  Download,
  FileCheck2,
  Flame,
  Globe2,
  Hotel,
  Languages,
  Luggage,
  MessageCircle,
  Navigation,
  Plane,
  ShieldAlert,
  Smartphone,
  Utensils,
  WifiOff,
} from "lucide-react";
import { tripDocuments, unionPayOptions } from "@/lib/travel";
import { TripWorkspaceNav } from "@/components/trip-workspace-nav";
import { CurrencyExchange } from "@/components/currency-exchange";
import { ManagedContentPanel } from "@/components/managed-content-panel";

const officialLinks = {
  visa:
    "https://english.www.gov.cn/news/202509/02/content_WS68b6ce1ac6d0868f4e8f5437.html",
  visaCenter: "https://bio.visaforchina.cn/MOW3_RU/qianzhengyewu",
  powerBank: "https://www.caac.gov.cn/XWZX/MHYW/202506/t20250626_227805.html",
  batteries: "https://www.caac.gov.cn/CXCK/HLZN/201512/t20151214_15866.html",
  prohibited: "https://www.caac.gov.cn/INDEX/HLFW/HKLXCS/202303/t20230316_217597.html",
  customs: "https://english.customs.gov.cn/",
  internet: "https://www.gov.uk/foreign-travel-advice/china/safety-and-security#internet-access",
};

const chinaApps = [
  {
    name: "Alipay",
    chineseName: "支付宝",
    icon: CreditCard,
    purpose: "Основная оплата по QR-коду, транспорт, такси и городские мини-приложения.",
    tip: "До вылета пройдите проверку по загранпаспорту, привяжите карту и сделайте резервный способ оплаты.",
    iosUrl: "https://apps.apple.com/us/app/alipay-simplify-your-life/id333206289",
    androidUrl: "https://play.google.com/store/apps/details?id=com.eg.android.AlipayGphone",
  },
  {
    name: "WeChat",
    chineseName: "微信",
    icon: MessageCircle,
    purpose: "Переписка с партнёрами, обмен контактами по QR-коду, звонки и WeChat Pay.",
    tip: "Зарегистрируйтесь заранее и сохраните контакты принимающей стороны до поездки.",
    iosUrl: "https://apps.apple.com/us/app/wechat/id414478124",
    androidUrl: "https://play.google.com/store/apps/details?id=com.tencent.mm",
  },
  {
    name: "AMap Global",
    chineseName: "高德地图",
    icon: Navigation,
    purpose: "Навигация по Китаю, общественный транспорт и поиск адресов на китайском.",
    tip: "Сохраните отель и выставочную площадку в избранное ещё до прилёта.",
    iosUrl: "https://apps.apple.com/us/app/amap-global/id461703208",
    androidUrl: "https://play.google.com/store/apps/details?id=com.autonavi.minimap",
  },
  {
    name: "DiDi Rider",
    chineseName: "滴滴出行",
    icon: CarFront,
    purpose: "Заказ официального такси с заранее известным маршрутом и стоимостью.",
    tip: "Показывайте водителю адрес по-китайски; DiDi также доступен как мини-приложение внутри Alipay.",
    iosUrl: "https://apps.apple.com/us/app/didi-rider-affordable-rides/id1362398401",
    androidUrl: "https://play.google.com/store/apps/details?id=com.sdu.didi.psnger",
  },
  {
    name: "Trip.com",
    chineseName: "携程旅行",
    icon: Hotel,
    purpose: "Отели, авиабилеты, железнодорожные билеты и поддержка на английском языке.",
    tip: "Проверяйте написание имени: для поездов оно должно совпадать с загранпаспортом.",
    iosUrl: "https://apps.apple.com/us/app/trip-com-book-flights-hotels/id681752345",
    androidUrl: "https://play.google.com/store/apps/details?id=ctrip.english",
  },
  {
    name: "Meituan",
    chineseName: "美团",
    icon: Utensils,
    purpose: "Рестораны, доставка еды, отзывы и другие городские услуги.",
    tip: "Интерфейс в основном китайский; для части услуг может понадобиться местный номер телефона.",
    iosUrl: "https://apps.apple.com/cn/app/%E7%BE%8E%E5%9B%A2-%E9%97%AE%E7%BE%8E%E5%9B%A2-%E9%83%BD%E5%AE%89%E6%8E%92/id423084029",
    androidUrl: "https://play.google.com/store/apps/details?id=com.sankuai.meituan",
  },
  {
    name: "Pleco",
    chineseName: "汉语词典",
    icon: Languages,
    purpose: "Офлайн-словарь, распознавание иероглифов и быстрый перевод надписей.",
    tip: "Загрузите словари и нужные офлайн-модули до вылета.",
    iosUrl: "https://apps.apple.com/us/app/pleco-chinese-dictionary/id341922306",
    androidUrl: "https://play.google.com/store/apps/details?id=com.pleco.chinesesystem",
  },
];

const limitedServices = [
  {
    title: "Google и YouTube",
    items: "Google Search, Gmail, Google Maps, Google Drive, YouTube и Google Play",
  },
  {
    title: "Социальные сети",
    items: "Facebook, Instagram, Messenger, Threads и X",
  },
  {
    title: "Мессенджеры",
    items: "WhatsApp, Telegram и Signal",
  },
  {
    title: "Справочные сервисы",
    items: "Wikipedia и часть иностранных новостных сайтов",
  },
];

const etiquette = [
  {
    icon: Utensils,
    title: "Палочки и еда",
    text: "Не втыкайте палочки вертикально в рис, не указывайте ими на людей и не передавайте еду из палочек в палочки.",
  },
  {
    icon: BriefcaseBusiness,
    title: "Деловое общение",
    text: "Будьте пунктуальны. Визитку и документы передавайте двумя руками; обращайтесь по фамилии и должности.",
  },
  {
    icon: Camera,
    title: "Фото и заводы",
    text: "Спрашивайте разрешение перед съёмкой людей, производственных линий и прототипов. Не фотографируйте охраняемые объекты.",
  },
  {
    icon: Smartphone,
    title: "Связь и оплата",
    text: "До вылета настройте Alipay или WeChat Pay, привяжите карту и сохраните адреса по-китайски. Держите резерв наличных.",
  },
];

export function TravelGuide() {
  return (
    <main className="radar-grid min-h-[calc(100vh-4rem)]">
      <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
        <div className="mb-5 flex justify-end"><TripWorkspaceNav active="rules" /></div>
        <section className="overflow-hidden rounded-2xl border border-white/9 bg-[#0a1516]/94">
          <div className="grid lg:grid-cols-[minmax(0,1fr)_420px]">
            <div className="p-5 sm:p-7 lg:p-9">
              <div className="flex items-center gap-2 text-sm font-semibold text-cyan-300">
                <Plane className="size-4" /> Деловая поездка в Китай
              </div>
              <h1 className="mt-4 max-w-3xl text-3xl font-semibold tracking-[-0.04em] text-white sm:text-5xl">
                Перед поездкой
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-400">
                Документы, приложения, оплата, багаж и правила поведения — всё,
                что стоит подготовить до вылета.
              </p>
            </div>

            <div className="border-t border-amber-300/20 bg-amber-300/[0.06] p-5 sm:p-7 lg:border-l lg:border-t-0">
              <div className="flex items-center gap-2 text-sm font-semibold text-amber-200">
                <ShieldAlert className="size-5" /> Виза: проверьте дату поездки
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                Граждане РФ с обычным загранпаспортом могут въезжать без визы
                до <strong className="text-white">14 сентября 2026 года включительно</strong>
                , на срок до 30 дней. Для более поздней поездки нужна виза либо
                официальное подтверждение продления режима.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <SourceLink href={officialLinks.visa}>Официальное правило</SourceLink>
                <SourceLink href={officialLinks.visaCenter}>Визовый центр КНР</SourceLink>
              </div>
              <p className="mt-4 text-xs text-amber-100/60">Сверено 2 сентября 2026 года.</p>
            </div>
          </div>
        </section>

        <section className="mt-6 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5 sm:p-7">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <FileCheck2 className="size-5 text-cyan-300" /> Комплект документов
            </div>
            <ul className="mt-5 grid gap-3 md:grid-cols-2">
              {tripDocuments.map((item, index) => (
                <li
                  key={item}
                  className="flex gap-3 rounded-xl border border-white/8 bg-[#071011]/70 p-4 text-sm leading-6 text-slate-400"
                >
                  <span className="grid size-6 shrink-0 place-items-center rounded-full bg-cyan-300/10 font-mono text-xs text-cyan-300">
                    {index + 1}
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <aside className="rounded-2xl border border-violet-400/15 bg-violet-400/[0.045] p-5 sm:p-6">
            <div className="flex items-center gap-2 font-semibold text-white">
              <Globe2 className="size-5 text-violet-300" /> Перед покупкой
            </div>
            <ol className="mt-5 space-y-4 text-sm leading-6 text-slate-400">
              <li>1. Проверьте въезд по дате на официальном сайте.</li>
              <li>2. Получите QR-код регистрации на выставку.</li>
              <li>3. Сравните билет с багажом и без него.</li>
              <li>4. Выбирайте отель у нужной площадки, а не только в центре города.</li>
              <li>5. Сохраните адрес отеля и выставки на китайском.</li>
            </ol>
          </aside>
        </section>

        <section className="mt-10">
          <SectionHeading
            eyebrow="Телефон до вылета"
            title="Приложения, которые пригодятся в Китае"
            text="Установите их в России, войдите в аккаунты и проверьте привязку карты. Магазин Google Play и часть зарубежных сервисов в материковом Китае могут не открываться."
          />
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {chinaApps.map(({ name, chineseName, icon: Icon, purpose, tip, iosUrl, androidUrl }) => (
              <article key={name} className="flex flex-col rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5">
                <div className="flex items-start justify-between gap-4">
                  <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-cyan-300/10 text-cyan-300">
                    <Icon className="size-5" />
                  </span>
                  <span className="text-sm font-medium text-slate-500">{chineseName}</span>
                </div>
                <h3 className="mt-4 text-lg font-semibold text-white">{name}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-300">{purpose}</p>
                <p className="mt-3 flex-1 text-xs leading-5 text-slate-500">{tip}</p>
                <div className="mt-5 grid grid-cols-2 gap-2">
                  <DownloadLink href={iosUrl}>iPhone</DownloadLink>
                  <DownloadLink href={androidUrl}>Android</DownloadLink>
                </div>
              </article>
            ))}
          </div>

          <div className="mt-5 rounded-2xl border border-orange-300/15 bg-orange-300/[0.045] p-5 sm:p-6">
            <div className="flex items-center gap-2 font-semibold text-white">
              <WifiOff className="size-5 text-orange-300" /> Что обычно недоступно в материковом Китае
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {limitedServices.map((group) => (
                <div key={group.title} className="rounded-xl border border-white/8 bg-[#071011]/70 p-4">
                  <h3 className="text-sm font-semibold text-slate-200">{group.title}</h3>
                  <p className="mt-2 text-xs leading-5 text-slate-500">{group.items}</p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-sm leading-6 text-slate-400">
              Доступ меняется в зависимости от сети. Сохраните билеты, адреса, переводы и нужные страницы офлайн. Корпоративный защищённый доступ согласуйте с ИТ-службой и используйте только в соответствии с законодательством КНР.
            </p>
            <div className="mt-3">
              <SourceLink href={officialLinks.internet}>Актуальное предупреждение об интернете</SourceLink>
            </div>
          </div>
        </section>

        <CurrencyExchange />

        <ManagedContentPanel />

        <section className="mt-8">
          <SectionHeading
            eyebrow="Оплата в Китае"
            title="Как оформить UnionPay в России"
            text="Подтверждённые варианты на 2 сентября 2026 года. Тарифы и зарубежная работоспособность меняются, поэтому карту нужно проверить до вылета и иметь резервный способ оплаты."
          />
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {unionPayOptions.map((option) => (
              <article key={option.bank} className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5">
                <CreditCard className="size-5 text-cyan-300" />
                <h3 className="mt-4 font-semibold text-white">{option.bank}</h3>
                <p className="mt-1 text-xs font-semibold uppercase tracking-[0.08em] text-violet-300">{option.status}</p>
                <p className="mt-4 text-sm leading-6 text-slate-400">{option.howToOpen}</p>
                <p className="mt-3 text-xs leading-5 text-slate-500">{option.cost}</p>
                <div className="mt-4"><SourceLink href={option.url}>Условия банка</SourceLink></div>
              </article>
            ))}
          </div>
          <div className="mt-4 rounded-xl border border-amber-300/18 bg-amber-300/[0.055] p-4 text-sm leading-6 text-slate-400">
            <strong className="text-amber-200">Практический минимум:</strong> активируйте карту, установите PIN, сделайте контрольную операцию, сохраните телефон банка и возьмите наличные юани. Не рассчитывайте только на бесконтактную оплату: терминал может потребовать вставить карту.
          </div>
        </section>

        <section className="mt-8">
          <SectionHeading
            eyebrow="Багаж и граница"
            title="Что проверить до аэропорта"
            text="Короткий список не заменяет правила авиакомпании и таможни, но закрывает самые частые ошибки."
          />

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <RuleCard icon={BatteryCharging} title="Power bank: CCC и ватт-часы" tone="cyan">
              <p>
                На внутренних рейсах КНР с 28 июня 2025 года нельзя брать
                устройство без читаемой маркировки CCC/3C, а также отозванную модель.
                Power bank перевозится только в ручной клади и не используется в полёте.
              </p>
              <p className="mt-3">
                До 100 Wh — без согласования; свыше 100 до 160 Wh — с разрешения
                авиакомпании, не более двух; свыше 160 Wh — запрещено. «10 000 mAh»
                при 3,7 V — примерно 37 Wh: лимит измеряется в Wh, а не в ваттах.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <SourceLink href={officialLinks.powerBank}>Правило CCC</SourceLink>
                <SourceLink href={officialLinks.batteries}>Лимиты батарей</SourceLink>
              </div>
            </RuleCard>

            <RuleCard icon={Flame} title="Зажигалки и источники огня" tone="orange">
              <p>
                Зажигалки, спички, электронные прикуриватели, магниевые огнива и
                самонагревающаяся еда запрещены и в ручной клади, и в багаже на
                рейсах гражданской авиации Китая.
              </p>
              <p className="mt-3">
                Не прячьте предмет в чемодан: на досмотре его изымут, а багаж могут
                задержать. Проверяйте также правила конкретного перевозчика.
              </p>
              <div className="mt-4">
                <SourceLink href={officialLinks.prohibited}>Список CAAC</SourceLink>
              </div>
            </RuleCard>

            <RuleCard icon={Luggage} title="Лекарства, образцы и продукты" tone="violet">
              <ul className="space-y-2">
                <li>• Лекарства — в заводской упаковке, в личном количестве; для рецептурных средств возьмите рецепт или справку.</li>
                <li>• Коммерческие образцы и оборудование — с перечнем, стоимостью и инвойсом; заранее уточните временный ввоз.</li>
                <li>• Мясо, молочные продукты, семена, растения и свежие продукты не берите без проверки карантинных правил.</li>
              </ul>
              <div className="mt-4">
                <SourceLink href={officialLinks.customs}>Таможня КНР</SourceLink>
              </div>
            </RuleCard>

            <RuleCard icon={CircleAlert} title="Важно" tone="neutral">
              <p>
                Правила зависят от маршрута, пересадок, авиакомпании и типа товара.
                Если предмет может считаться опасным, коммерческим или подлежащим
                карантину, получите письменное подтверждение до вылета.
              </p>
              <p className="mt-3">
                Этот раздел — практическая памятка, а не юридическое или таможенное заключение.
              </p>
            </RuleCard>
          </div>
        </section>

        <section className="mt-10">
          <SectionHeading
            eyebrow="Культурный код"
            title="Простые правила, которые помогают"
            text="Это нормы вежливости, а не строгие законы; в разных регионах и компаниях стиль общения отличается."
          />
          <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {etiquette.map(({ icon: Icon, title, text }) => (
              <article key={title} className="rounded-2xl border border-white/8 bg-[#0a1516]/90 p-5">
                <Icon className="size-5 text-cyan-300" />
                <h3 className="mt-4 font-semibold text-white">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-white/8 bg-[#071011]/85 p-5 text-sm leading-6 text-slate-500 sm:p-6">
          <strong className="text-slate-300">Дисклеймер.</strong> Цены и правила могут измениться без предупреждения.
          Непосредственно перед вылетом повторно проверьте документы, билет, отель,
          авиакомпанию, CAAC, таможню КНР и условия конкретной выставки.
        </section>
      </div>
    </main>
  );
}

function SectionHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-300">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white sm:text-3xl">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{text}</p>
    </div>
  );
}

function SourceLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-300 hover:text-cyan-200"
    >
      {children} <ArrowUpRight className="size-3.5" />
    </a>
  );
}

function DownloadLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-10 items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.035] px-3 text-xs font-semibold text-slate-200 transition-colors hover:border-cyan-300/30 hover:bg-cyan-300/10 hover:text-cyan-200"
    >
      {children} <Download className="size-3.5" />
    </a>
  );
}

function RuleCard({
  icon: Icon,
  title,
  tone,
  children,
}: {
  icon: typeof BatteryCharging;
  title: string;
  tone: "cyan" | "orange" | "violet" | "neutral";
  children: React.ReactNode;
}) {
  const tones = {
    cyan: "border-cyan-300/15 text-cyan-300",
    orange: "border-orange-300/15 text-orange-300",
    violet: "border-violet-300/15 text-violet-300",
    neutral: "border-white/10 text-slate-300",
  };
  return (
    <article className={`rounded-2xl border bg-[#0a1516]/90 p-5 sm:p-6 ${tones[tone]}`}>
      <div className="flex items-center gap-2 font-semibold text-white">
        <Icon className={`size-5 ${tones[tone].split(" ")[1]}`} /> {title}
      </div>
      <div className="mt-4 text-sm leading-6 text-slate-400">{children}</div>
    </article>
  );
}
