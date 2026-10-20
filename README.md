## Как запустить приложение

```bash
cp .env.example .env
make build-d
```

API: http://localhost:8080

Swagger: http://localhost:8080/docs

```text
X-API-Key: secret-key
```

## Как создать платеж:

```bash
curl -i -X POST http://localhost:8080/api/v1/payments \
  -H 'X-API-Key: secret-key' \
  -H 'Idempotency-Key: 007-013' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": "199.90",
    "currency": "RUB",
    "description": "Заказ №42",
    "metadata": {"order_id": 42},
    "webhook_url": "https://httpbin.org/post"
  }'
```

Успешный ответ имеет статус `202 Accepted`:

```json
{
  "payment_id": "0cfdf41a-8ae8-46b6-841b-58acfd85a366",
  "status": "pending",
  "created_at": "2026-10-15T06:00:00Z"
}
```

## Получение платежа

Подставьте `payment_id`, полученный при создании платежа:

```bash
PAYMENT_ID='0cfdf41a-8ae8-46b6-841b-58acfd85a366'

curl -i \
  -H 'X-API-Key: secret-key' \
  "http://localhost:8080/api/v1/payments/${PAYMENT_ID}"
```

Пример ответа:

```json
{
  "payment_id": "0cfdf41a-8ae8-46b6-841b-58acfd85a366",
  "amount": "199.90",
  "currency": "RUB",
  "description": "Заказ №42",
  "metadata": {"order_id": 42},
  "status": "succeeded",
  "idempotency_key": "007-013",
  "webhook_url": "https://httpbin.org/post",
  "created_at": "2026-10-15T06:00:00Z",
  "processed_at": "2026-10-15T06:00:03Z"
}
```
