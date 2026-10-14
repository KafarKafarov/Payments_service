from faststream.rabbit import RabbitBroker

from app.core.config import settings

rabbit_broker = RabbitBroker(settings.RABBIT_URL)
