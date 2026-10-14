from fastapi import FastAPI

from app.api.routers.payments import router as payments_router

app = FastAPI(
    title='Платежный сервис',
    version='0.0.1',
)
app.include_router(payments_router)
