# graphql-gateway-demo

[![CI](https://github.com/TaeseobK/graphql-gateway-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/TaeseobK/graphql-gateway-demo/actions/workflows/ci.yml)

A small, self-contained example of the **API gateway pattern** I use for microservice backends: a FastAPI + Strawberry GraphQL gateway that enforces permissions in one place, calls downstream services, and fans events out with Redis Streams.

It contains no company code. The downstream service is an in-memory stand-in so the demo runs on its own.

## Architecture

`@mermaid
flowchart LR
    Client -->|"GraphQL + Bearer token"| Gateway
    subgraph Gateway["Gateway (FastAPI + Strawberry)"]
        Auth["Token decode + permission check"]
        Resolvers
        Auth --> Resolvers
    end
    Resolvers -->|"HTTP (httpx)"| Employee["Employee service"]
    Resolvers -->|"XADD employee.events"| Stream[("Redis Stream")]
    Stream -->|"consumer group: notifications"| N["Notification worker"]
    Stream -->|"consumer group: audit"| A["Audit worker"]
`@

## Ideas shown here

- **Permissions at the gateway.** Each GraphQL field declares the permission code it needs (`employee.read`, `employee.write`). Downstream services never re-implement the check. See `app/auth.py` and `app/schema.py`.
- **Dependency injection for clients.** The HTTP client and Redis client are passed into `create_app`, so tests swap in an in-process service and `fakeredis`, with no network.
- **Event fan-out.** A mutation publishes one event to a Redis Stream. Every consumer group receives its own copy and acknowledges independently. See `app/events.py`.

## Run the tests

`@bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
`@

The tests cover: anonymous requests are denied, a reader can list and filter, a reader cannot write, and one write reaches every consumer group.

## Run it locally

`@bash
export GATEWAY_JWT_SECRET="a-long-random-secret"
export EMPLOYEE_SERVICE_URL="http://localhost:8001"
export REDIS_URL="redis://localhost:6379/0"

uvicorn app.fake_employee_service:create_service --factory --port 8001 &
uvicorn app.main:create_app --factory --port 8000
`@

GraphQL is served at `http://localhost:8000/graphql`. Tokens are HS256 JWTs with a `permissions` claim (see `issue_token` in `app/auth.py`). Reads work without Redis running; mutations need a Redis instance because they publish an event.

## Scope and limits

This is a teaching-sized example: one downstream service, a shared-secret token, and no persistence. A production setup would issue tokens from a dedicated auth service, add rate limiting and tracing, and run consumers as separate workers.

## License

MIT
