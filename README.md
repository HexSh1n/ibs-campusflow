# IBS CampusFlow API

Бэкенд для сервиса бронирования аудиторий на Python (FastAPI + SQLite).

## Запуск

Сервер:
```powershell
d:\ibs\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger UI открывается на `http://127.0.0.1:8000/docs`.

Тесты и покрытие:
```powershell
d:\ibs\.venv\Scripts\python.exe -m pytest -v
d:\ibs\.venv\Scripts\python.exe -m coverage run --source=app -m pytest -q
d:\ibs\.venv\Scripts\python.exe -m coverage report --skip-empty
```

## База и seed-данные

При первом старте, если таблица `users` пуста, база создаётся сама и заполняется начальными данными от текущей даты (`0` — сегодня, `+1` — завтра, `+2` — послезавтра). Путь к файлу можно переопределить через `CAMPUSFLOW_DB` (по умолчанию `campusflow.db`).

Сбросить базу и залить сиды заново перед демо:
```powershell
d:\ibs\.venv\Scripts\python.exe -m app.seed --reset
```

Пользователи из seed (`password == login`):
- `student1` (`Иван Студентов`, `student`) — токен `mock-token-student1`
- `student2` (`Мария Студентова`, `student`) — токен `mock-token-student2`
- `admin` (`Администратор Пупкин`, `admin`) — токен `mock-token-admin`

## Соглашения

- Авторизация только через `Authorization: Bearer mock-token-<login>`, заголовок `X-User-Id` не используется.
- Все ручки `/api/rooms*` публичные.
- Бронирование на сегодняшнюю дату на уже прошедшее время отклоняется с `400 VALIDATION_ERROR`.
- `DELETE /api/bookings/{id}` отменяет только свою бронь; чужую (даже админ) отменять через неё нельзя — вернётся `403 FORBIDDEN`. Для админской отмены есть `DELETE /api/admin/bookings/{id}`.
- Проверка пересечений в `POST /api/bookings` идёт в транзакции `BEGIN IMMEDIATE` после проверки auth (`401`), полей/дат (`400`) и наличия аудитории (`404`). Касание границ (например `10:00–11:30` и `11:30–14:00`) конфликтом не считается.

## Формат ошибок

Все ошибки возвращаются в JSON UTF-8 в виде `{"code": "...", "message": "...", "details": {...}}`:
`VALIDATION_ERROR` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `ROOM_NOT_FOUND` (404), `BOOKING_NOT_FOUND` (404), `NOT_FOUND` (404), `BOOKING_CONFLICT` (409), `ALREADY_CANCELLED` (409), `INTERNAL_ERROR` (500).

## Ручки API

- `GET /api/health` — проверка живости сервиса
- `POST /api/auth/login` — вход по `{login, password}`
- `GET /api/rooms` — список аудиторий (`building`, `minCapacity`, `equipment`)
- `GET /api/rooms/available` *(бонус)* — свободные аудитории на `date` (и опционально `startTime`/`endTime`) с фильтрами комнат
- `GET /api/rooms/{id}` — карточка аудитории
- `GET /api/rooms/{id}/free-slots?date=YYYY-MM-DD` — свободные окна в пределах `09:00–18:00`
- `POST /api/bookings` — создать бронь (`userId` берётся из токена)
- `GET /api/bookings/my` — свои брони (опционально `status=active|cancelled`)
- `DELETE /api/bookings/{id}` — отменить свою бронь
- `GET /api/admin/bookings` — все брони (фильтры `date`, `roomId`, `userId`, `status`)
- `DELETE /api/admin/bookings/{id}` — админская отмена любой брони
- `POST /api/admin/rooms` — добавить аудиторию
- `PUT /api/admin/rooms/{id}` — обновить аудиторию

Примеры:
```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"student1","password":"student1"}'

curl -s "http://127.0.0.1:8000/api/rooms/available?date=2026-11-16&startTime=11:30&endTime=14:00&building=A"

curl -s -X POST http://127.0.0.1:8000/api/bookings \
  -H "Authorization: Bearer mock-token-student1" \
  -H "Content-Type: application/json" \
  -d '{"roomId":2,"date":"2026-11-16","startTime":"10:00","endTime":"11:30","comment":"Семинар"}'
```
