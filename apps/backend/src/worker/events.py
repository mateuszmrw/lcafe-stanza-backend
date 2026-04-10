import json
import uuid

from redis.asyncio import Redis


async def publish_import_event(
    redis: Redis,
    content_item_id: uuid.UUID,
    event_type: str,
    data: dict,
) -> None:
    """Publish a book-import lifecycle event to the per-item Redis pub/sub channel.

    Consumers (the SSE endpoint) subscribe to `import:{content_item_id}`.
    """
    channel = f"import:{content_item_id}"
    payload = json.dumps({"event": event_type, "data": data})
    await redis.publish(channel, payload)
