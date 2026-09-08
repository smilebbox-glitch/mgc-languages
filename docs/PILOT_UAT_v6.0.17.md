# MGC Language Lab — Pilot UAT v6.0.17

## How to use

Execute this checklist on the actual pilot environment with real pilot-role accounts. Record `PASS`, `FAIL`, evidence and defect severity for every row.

Severity:

- **S1** — security/data loss/service unavailable for all users.
- **S2** — core learning/role function blocked for a user group.
- **S3** — non-blocking functional defect.
- **S4** — cosmetic/content improvement.

Launch rule: **no open S1/S2 defects**.

## A. Access and identity

| ID | Role | Scenario | Expected |
|---|---|---|---|
| A01 | User | Open pilot URL from PC #1 | Login page loads over approved company URL |
| A02 | User | Authenticate | Correct user profile and department load |
| A03 | User | Refresh browser | Session remains valid within configured TTL |
| A04 | User | Logout | Session is terminated and learning UI is hidden |
| A05 | Manager | Authenticate | `Руководитель` appears |
| A06 | Admin | Authenticate | `Админ` appears |
| A07 | User | Try direct manager/admin access | Access denied |
| A08 | Manager | Open team data | Only permitted department is visible |

## B. Chinese language track

| ID | Scenario | Expected |
|---|---|---|
| C01 | Select `Китайский язык · 中文` | Chinese track becomes active and is saved |
| C02 | Open Home | Approved Chinese pilot design renders |
| C03 | Sidebar | `Информация о китайском` is visible |
| C04 | Phrase of the day | Chinese phrase, Pinyin and Russian meaning render |
| C05 | Phrase audio | Phrase plays through server TTS or browser fallback |
| C06 | Open Topics | Chinese terms load |
| C07 | Open Test | Quiz loads and can be completed |
| C08 | Open Scenario | Roleplay can be completed |
| C09 | Open 30-day course | Daily course content loads and progress saves |
| C10 | Open final exam | Exam result saves successfully |

## C. English language track

| ID | Scenario | Expected |
|---|---|---|
| E01 | Select `English` | English track becomes active and is saved |
| E02 | Open Home | Approved English pilot design renders |
| E03 | Sidebar | No `About English`; no Chinese-info item |
| E04 | Phrase of the day | Phrase and supporting copy are English |
| E05 | Home UI | General navigation/chrome remains Russian by design |
| E06 | Open Topics | English terms load |
| E07 | Phrase/term audio | English pronunciation plays |
| E08 | Complete quiz/scenario | Result and XP/progress save |

## D. Daily phrase rotation

| ID | Scenario | Expected |
|---|---|---|
| D01 | Two PCs on same calendar day | Same language shows the same phrase |
| D02 | Compare Chinese vs English | Each track shows its own language-specific phrase |
| D03 | Advance test clock/date in controlled environment | Next calendar day selects a different phrase |
| D04 | Daily illustration | Illustration path changes on consecutive days |
| D05 | Keep Home open across midnight | Home refreshes after midnight timer fires |

## E. Progress and persistence

| ID | Scenario | Expected |
|---|---|---|
| P01 | Complete learning action | Relevant progress changes |
| P02 | Earn XP | XP value updates |
| P03 | Close and reopen browser | Progress remains |
| P04 | Restart app container | Progress remains |
| P05 | Restart full stack without deleting volumes | Progress remains |
| P06 | User A vs User B | Progress is isolated per user |

## F. Games and notifications

| ID | Scenario | Expected |
|---|---|---|
| G01 | Open Games | Enabled pilot games load |
| G02 | Finish game | Result is saved and quota rules apply |
| G03 | Open notification icon | Notification settings/pending items load |
| G04 | Read/dismiss nudge | State persists and item does not reappear incorrectly |

## G. Manager and Admin

| ID | Role | Scenario | Expected |
|---|---|---|---|
| M01 | Manager | Open team list | Department-safe employee list |
| M02 | Manager | Open employee detail | Learning statistics load |
| AD01 | Admin | Open analytics | KPI/user/telemetry data load |
| AD02 | Editor | Open content governance | Terms/taxonomy/question quality only |
| AD03 | Editor | Try admin-only control | Access denied |
| AD04 | Admin | Create/import term in test content | Workflow accepts valid content |
| AD05 | Admin | Submit/review/approve content | Governance states update |
| AD06 | Admin | Open pilot governance | Groups/features/assignments load |
| AD07 | Admin | Change test pilot flag | Only intended pilot group behavior changes |
| AD08 | Admin | Open IT dashboard | Readiness/alerts/recovery evidence load |

## H. Reliability and recovery

| ID | Scenario | Expected |
|---|---|---|
| R01 | `/health/live` | 2xx |
| R02 | `/health/ready` | 2xx before users are invited |
| R03 | Backup job | New backup + checksum appear |
| R04 | Restore evidence | Current per configured maximum age |
| R05 | Temporary DB interruption drill (IT only) | UI fails safely; no silent corruption |
| R06 | TTS unavailable | Browser fallback works or clear non-destructive error appears |

## I. Browser/LAN matrix

Minimum:

| Client | Browser | Result |
|---|---|---|
| PC #1 | Company-standard Chrome/Chromium | |
| PC #2 | Company-standard Edge/Chromium | |
| Optional mobile/tablet | Supported corporate browser | |

Validate Home, Topics, Test, Scenario, language switch and logout on each required browser.

## J. Pilot feedback questions

Ask each Wave 1 user after day 3 and day 10:

1. Было ли понятно, с чего начать обучение без инструкции?
2. Какая функция оказалась полезнее всего?
3. Что на главной странице лишнее или непонятное?
4. Полезна ли «Фраза дня» для вашей реальной работы?
5. Достаточно ли понятны термины и сценарии для вашего подразделения?
6. Возникали ли задержки, ошибки или потеря прогресса?
7. Хотели бы вы пользоваться сервисом после пилота?

## Pilot decision record

- Date:
- Environment/commit:
- Participants invited:
- UAT S1 open:
- UAT S2 open:
- S3/S4 actions:
- Backup evidence checked by:
- Identity/TLS checked by:
- Product owner decision: `GO / GO WITH ACTIONS / NO-GO`
- IT owner decision: `GO / NO-GO`
- Notes:
