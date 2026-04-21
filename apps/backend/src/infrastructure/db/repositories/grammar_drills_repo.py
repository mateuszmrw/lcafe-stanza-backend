from __future__ import annotations

import json

from redis.asyncio import Redis

_KEY_PREFIX = "grammar:session:"
_TTL_SECONDS = 30 * 60  # 30 minutes


class GrammarDrillsRepository:
    def _key(self, session_id: str) -> str:
        return f"{_KEY_PREFIX}{session_id}"

    async def store_session(
        self, redis: Redis, session_id: str, questions: list[dict]
    ) -> None:
        """Persist question answers for scoring. Stored keyed by question id."""
        data = {
            q["id"]: {
                "accepted_forms": q.get("accepted_forms", [q["correct_form"]]),
                "correct_form": q["correct_form"],
                "lemma": q["lemma"],
                "form_type": q["form_type"],
            }
            for q in questions
        }
        await redis.setex(self._key(session_id), _TTL_SECONDS, json.dumps(data))

    async def get_session(self, redis: Redis, session_id: str) -> dict | None:
        raw = await redis.get(self._key(session_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def delete_session(self, redis: Redis, session_id: str) -> None:
        await redis.delete(self._key(session_id))
