from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import login, records, search, webhooks

app = FastAPI(title="Records API", version="0.1.0")

app.include_router(login.router)
app.include_router(records.router)
app.include_router(search.router)
app.include_router(webhooks.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "path": str(request.url.path),
            "detail": repr(exc),
        },
    )
