# LOCAL_SETUP

## 1) Что запускается в этом репозитории

- `integration-service` (FastAPI) на `http://localhost:8090`
- `pixel-backend` (FastAPI) на `http://localhost:8000`
- `bot` (Telegram bot)

`zammad-develop` и `erpnext-develop` в этом workspace используются как исходники.
Рабочие локальные стенды Zammad/ERPNext поднимайте в их официальных docker-стеках.

## 2) Порты

- `8090` - integration-service
- `8000` - pixel-backend
- `8080` - типичный порт Zammad (зависит от выбранного стека)
- `8081` - пример порта ERPNext (зависит от выбранного стека)

## 3) Подготовка env

Создайте файлы:

- `integration-service/.env` по `integration-service/.env.example`
- `pixel-backend/.env` по `pixel-backend/.env.example`
- `bot/.env` по `bot/.env.example`

Минимум для `integration-service/.env`:

```env
INTEGRATION_TOKEN=super_secret_token
ZAMMAD_BASE_URL=http://host.docker.internal:8080
ZAMMAD_TOKEN=your_zammad_api_token
ENABLE_ERP_ISSUE=false
```

Минимум для `pixel-backend/.env`:

```env
BOT_API_TOKEN=S3cr3t_PixelSC_2026
INTEGRATION_URL=http://integration-service:8090
INTEGRATION_TOKEN=super_secret_token
```

Минимум для `bot/.env`:

```env
BOT_TOKEN_TELEGRAM=...
BACKEND_URL=http://pixel-backend:8000
BOT_API_TOKEN=S3cr3t_PixelSC_2026
```

## 4) Как получить API токены

Zammad:
1. Откройте профиль пользователя в Zammad.
2. Перейдите в раздел токенов API (Personal Access Token).
3. Создайте токен и укажите его в `ZAMMAD_TOKEN`.

ERPNext:
1. Откройте User в ERPNext.
2. В секции API Access сгенерируйте `API Key` и `API Secret`.
3. Укажите их в `ERPNEXT_API_KEY` и `ERPNEXT_API_SECRET`.
4. Включите `ENABLE_ERP_ISSUE=true` в `integration-service/.env`.

## 5) Запуск

```bash
docker compose -f infra/docker-compose.local.yml up -d --build
```

## 6) Тест backend через curl

```bash
curl -X POST "http://localhost:8000/api/orders" ^
  -H "X-Bot-Token: S3cr3t_PixelSC_2026" ^
  -H "Content-Type: application/json" ^
  -d "{\"branch_id\":1,\"client_name\":\"Иван\",\"client_phone\":\"+79990000000\",\"client_telegram\":\"123\",\"device_type\":\"Смартфон\",\"model\":\"iPhone 13\",\"problem_description\":\"Не включается\"}"
```

```bash
curl -X GET "http://localhost:8000/api/orders" ^
  -H "X-Bot-Token: S3cr3t_PixelSC_2026"
```
