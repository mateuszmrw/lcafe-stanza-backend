"""AnkiConnect helper functions."""
from __future__ import annotations

import logging

import httpx

from src.infrastructure.anki.model_definition import SLOVO_MODEL_NAME, get_create_model_params

logger = logging.getLogger(__name__)


async def ensure_slovo_model(anki_url: str) -> bool:
    """Check if the Slovo model exists in Anki; create it if missing.

    Returns True if the model exists or was created successfully.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        # Check existing models
        resp = await client.post(
            anki_url,
            json={"action": "modelNames", "version": 6},
        )
        data = resp.json()
        models = data.get("result", [])

        if SLOVO_MODEL_NAME in models:
            return True

        # Create the model
        logger.info("Creating Anki model '%s'", SLOVO_MODEL_NAME)
        resp = await client.post(
            anki_url,
            json={
                "action": "createModel",
                "version": 6,
                "params": get_create_model_params(),
            },
        )
        result = resp.json()
        if result.get("error"):
            logger.error("Failed to create Anki model: %s", result["error"])
            return False

        return True


async def store_media_file(anki_url: str, filename: str, data_base64: str) -> bool:
    """Upload a media file to Anki via AnkiConnect's storeMediaFile."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            anki_url,
            json={
                "action": "storeMediaFile",
                "version": 6,
                "params": {
                    "filename": filename,
                    "data": data_base64,
                },
            },
        )
        result = resp.json()
        if result.get("error"):
            logger.warning("Failed to store media file %s: %s", filename, result["error"])
            return False
        return True
