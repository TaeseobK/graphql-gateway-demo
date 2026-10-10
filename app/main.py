"""Gateway app: FastAPI + Strawberry GraphQL, with downstream clients injected."""
import os

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from strawberry.fastapi import GraphQLRouter

from .auth import decode_token
from .schema import schema


def create_app(upstream: httpx.AsyncClient | None = None, redis=None) -> FastAPI:
    upstream = upstream or httpx.AsyncClient(
        base_url=os.getenv("EMPLOYEE_SERVICE_URL", "http://localhost:8001")
    )
    redis = redis or aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True
    )

    async def get_context(request: Request) -> dict:
        return {
            "user": decode_token(request.headers.get("authorization")),
            "upstream": upstream,
            "redis": redis,
        }

    app = FastAPI(title="graphql-gateway-demo")
    app.include_router(GraphQLRouter(schema, context_getter=get_context), prefix="/graphql")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
