export type TripBudgetDefaults = {
  flightPerPerson: number;
  hotelPerRoomNight: number;
  ticketPerPerson: number;
  localTransportPerPerson: number;
  dailyAllowancePerPerson: number;
  documentsPerPerson: number;
};

export const tripBudgetDefaults: Record<string, TripBudgetDefaults> = {
  "citexpo-2026": {
    flightPerPerson: 75000,
    hotelPerRoomNight: 11000,
    ticketPerPerson: 0,
    localTransportPerPerson: 8000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 5000,
  },
  "china-nev-icv-2026": {
    flightPerPerson: 60000,
    hotelPerRoomNight: 8000,
    ticketPerPerson: 0,
    localTransportPerPerson: 9000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
  "bauma-china-2026": {
    flightPerPerson: 68000,
    hotelPerRoomNight: 12000,
    ticketPerPerson: 960,
    localTransportPerPerson: 9000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
  "auto-tech-guangzhou-2026": {
    flightPerPerson: 68000,
    hotelPerRoomNight: 13000,
    ticketPerPerson: 0,
    localTransportPerPerson: 9000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
  "auto-guangzhou-2026": {
    flightPerPerson: 68000,
    hotelPerRoomNight: 13000,
    ticketPerPerson: 1200,
    localTransportPerPerson: 10000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
  "automechanika-shanghai-2026": {
    flightPerPerson: 68000,
    hotelPerRoomNight: 12000,
    ticketPerPerson: 0,
    localTransportPerPerson: 9000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
  "capas-chengdu-2027": {
    flightPerPerson: 68000,
    hotelPerRoomNight: 9000,
    ticketPerPerson: 0,
    localTransportPerPerson: 9000,
    dailyAllowancePerPerson: 6000,
    documentsPerPerson: 18000,
  },
};

export const tripBudgetNotice =
  "Расчёт ориентировочный. Поля можно заменить фактическими коммерческими предложениями перед согласованием.";
