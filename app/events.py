"""Event fan-out with Redis Streams: one stream, one consumer group per subscriber."""
from redis.exceptions import ResponseError


async def publish(redis, stream: str, event: dict) -> str:
    """Append an event to the stream and return its id."""
    return await redis.xadd(stream, {key: str(value) for key, value in event.items()})


async def ensure_group(redis, stream: str, group: str) -> None:
    """Create a consumer group (and the stream) if it does not exist yet."""
    try:
        await redis.xgroup_create(stream, group, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def consume(redis, stream: str, group: str, consumer: str, count: int = 10) -> list[dict]:
    """Read new events for a group, acknowledge them, and return them."""
    response = await redis.xreadgroup(group, consumer, {stream: ">"}, count=count)
    events = []
    for _, messages in response or []:
        for message_id, fields in messages:
            events.append({"id": message_id, **fields})
            await redis.xack(stream, group, message_id)
    return events
