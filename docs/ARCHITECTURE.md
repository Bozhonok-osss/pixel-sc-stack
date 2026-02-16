# ARCHITECTURE

## Компоненты

- Telegram Bot (`bot/app/main.py`) - ведёт диалог с клиентом.
- Pixel Backend (`pixel-backend/app/main.py`) - основной API для бота.
- Integration Service (`integration-service/app/main.py`) - шлюз во внешние системы.
- Zammad - основной интерфейс операторов и тикеты.
- ERPNext - опциональный учётный контур.

## Поток данных

1. Пользователь в Telegram проходит FSM-диалог в боте.
2. Бот отправляет `POST /api/orders` в `pixel-backend`.
3. `pixel-backend` сохраняет заказ в sqlite и генерирует внутренний номер `PIX-YYYYMM-XXXX`.
4. `pixel-backend` вызывает `integration-service /api/intake`.
5. `integration-service` создаёт тикет в Zammad и (опционально) Issue в ERPNext, с idempotency и auth.
6. Номера внешних сущностей сохраняются в `pixel-backend` и возвращаются боту.
7. Бот показывает клиенту номер заявки.

## Почему так

- Все endpoint-ы, которые нужны боту (`orders`, `branches`, `support-staff`, `analytics`, `reports`), собраны в одном backend.
- Интеграционная логика с Zammad/ERPNext изолирована в отдельном сервисе.
- `zammad-develop` и `erpnext-develop` не изменяются.
