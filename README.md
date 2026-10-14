## Как запустить приложение

```bash
cp .env.example .env
make build-d
```

API: http://localhost:8080

Swagger: http://localhost:8080/docs


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
