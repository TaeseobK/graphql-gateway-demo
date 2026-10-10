import fakeredis.aioredis
import httpx
import pytest

from app.auth import issue_token
from app.events import consume, ensure_group
from app.fake_employee_service import create_service
from app.main import create_app
from app.schema import EVENT_STREAM

LIST_QUERY = "{ employees { id name department } }"
ADD_MUTATION = 'mutation { addEmployee(name: "Citra", department: "hr") { id name department } }'


@pytest.fixture
async def redis():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client(redis):
    upstream = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_service()), base_url="http://upstream"
    )
    app = create_app(upstream=upstream, redis=redis)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://gateway") as c:
        yield c


async def gql(client, query, permissions=None):
    headers = {"Authorization": f"Bearer {issue_token('tester', permissions)}"} if permissions is not None else {}
    response = await client.post("/graphql", json={"query": query}, headers=headers)
    return response.json()


async def test_anonymous_request_is_denied(client):
    body = await gql(client, LIST_QUERY)
    assert body["data"] is None
    assert body["errors"][0]["message"] == "Permission denied"


async def test_reader_can_list_employees(client):
    body = await gql(client, LIST_QUERY, ["employee.read"])
    assert [e["name"] for e in body["data"]["employees"]] == ["Ayu", "Budi"]


async def test_filter_is_passed_downstream(client):
    body = await gql(client, '{ employees(department: "finance") { name } }', ["employee.read"])
    assert body["data"]["employees"] == [{"name": "Ayu"}]


async def test_reader_cannot_write(client):
    body = await gql(client, ADD_MUTATION, ["employee.read"])
    assert body["errors"][0]["message"] == "Permission denied"


async def test_write_publishes_event_to_every_consumer_group(client, redis):
    for group in ("notifications", "audit"):
        await ensure_group(redis, EVENT_STREAM, group)

    body = await gql(client, ADD_MUTATION, ["employee.write"])
    assert body["data"]["addEmployee"]["name"] == "Citra"

    for group in ("notifications", "audit"):
        events = await consume(redis, EVENT_STREAM, group, consumer="worker-1")
        assert len(events) == 1
        assert events[0]["type"] == "employee.created"
        assert events[0]["name"] == "Citra"
