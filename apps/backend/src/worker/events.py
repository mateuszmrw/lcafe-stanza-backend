import json
import uuid

from redis.asyncio import Redis

from src.domain.content.import_service import IMPORT_CHANNEL


async def publish_import_event(
    redis: Redis,
    content_item_id: uuid.UUID,
    event_type: str,
    data: dict,
) -> None:
    """Publish a book-import lifecycle event to the per-item Redis pub/sub channel.

    Consumers (the SSE endpoint) subscribe to `import:{content_item_id}`.
    """
    channel = IMPORT_CHANNEL.format(book_id=content_item_id)
    payload = json.dumps({"event": event_type, "data": data})
    await redis.publish(channel, payload)
