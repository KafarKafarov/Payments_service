import logging
from uuid import UUID

import httpx

from app.core.config import settings
from app.core.constants import WEBHOOK_ID_HEADER_NAME
from app.db.models.payment import PaymentStatus

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    pass


class WebhookClient:
    async def send(
        self,
        *,
        url: str,
        payment_id: UUID,
        status: PaymentStatus,
    ) -> None:
        payload = {
            'payment_id': str(payment_id),
            'status': status.value,
        }
        headers = {WEBHOOK_ID_HEADER_NAME: str(payment_id)}

        logger.info(
            f'Webhook: отправка уведомления payment_id={payment_id}, '
            f'url={url}, status={status.value}'
        )
        try:
            async with httpx.AsyncClient(
                timeout=settings.webhook_timeout
            ) as client:
                response = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                )
                logger.info(
                    f'Webhook: получен ответ payment_id={payment_id}, '
                    f'http_status={response.status_code}'
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            reasons = {
                400: 'сервер отклонил содержимое уведомления',
                401: 'сервер требует авторизацию',
                403: 'сервер запретил доступ',
                404: 'обработчик webhook по этому адресу не найден',
                405: 'сервер не принимает POST по этому адресу; '
                'укажите URL обработчика webhook, принимающего POST',
                429: 'сервер ограничил частоту запросов',
            }
            reason = reasons.get(
                code,
                'ошибка на стороне сервера webhook'
                if code >= 500
                else 'сервер вернул неуспешный ответ',
            )
            raise WebhookError(f'HTTP {code}: {reason}; url={url}') from exc
        except httpx.TimeoutException as exc:
            raise WebhookError(
                f'сервер не ответил за {settings.webhook_timeout} сек.; '
                f'url={url}'
            ) from exc
        except httpx.RequestError as exc:
            raise WebhookError(
                f'не удалось выполнить запрос к серверу webhook '
                f'({type(exc).__name__}); проверьте адрес, '
                f'доступность сервера и сеть; url={url}'
            ) from exc
