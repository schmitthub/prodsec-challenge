from fastapi import APIRouter

from app.api.routes import login, records, search, users, webhooks

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(records.router)
api_router.include_router(search.router)
api_router.include_router(webhooks.router)
