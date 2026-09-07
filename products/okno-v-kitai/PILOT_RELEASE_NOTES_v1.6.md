# Окно в Китай — Pilot v1.6
## UX & Business Operations

v1.6 переводит корпоративный пилот от общего информационного портала к персональному рабочему инструменту сотрудника, сохраняя security/reliability/governance baseline v1.5.

### Пользовательские функции
- новый `/my` с подписками, уведомлениями, избранным и активной поездкой;
- подписки по брендам, рынкам, темам, городам и мероприятиям;
- scheduler-generated in-app notifications с дедупликацией;
- FavoriteButton встроен в новости и календарь;
- personal trip сохраняется в SQLite;
- downloadable standalone HTML Offline Travel Pack;
- travel pack включает поездку, FX snapshot, managed travel content и избранное.

### Business operations
- `usage_events` с page_view, favorite_add/remove, trip_save, offline_pack_download;
- `/api/admin/usage` и административная агрегированная панель за 30 дней;
- `USAGE_RETENTION_DAYS`, cleanup выполняется scheduler.

### Privacy
- SQLite schema v3;
- user key = HMAC-SHA256 от SSO subject либо случайного device id;
- raw e-mail/ФИО не записываются в user tables;
- `USER_DATA_HMAC_KEY` — blocking config requirement для controlled pilot;
- external push/email notifications отсутствуют намеренно.

### Upgrade
Миграция v3 идемпотентно создаёт `user_preferences`, `user_favorites`, `user_trips`, `user_notifications`, `usage_events`. Существующие v1.5 tables/data не пересоздаются.
