from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Transaction Agent API",
    description="Ask natural-language questions about transaction data stored in Postgres.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
