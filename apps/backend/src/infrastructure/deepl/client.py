import httpx

from src.domain.ports.translation_port import TranslationPort

_API_FREE = "https://api-free.deepl.com/v2/translate"
_API_PRO = "https://api.deepl.com/v2/translate"


class DeepLClient(TranslationPort):
    """TranslationPort implementation using the DeepL API (BYOK)."""

    def __init__(self, api_key: str, timeout: float = 10.0) -> None:
        self._api_key = api_key
        self._timeout = timeout
        # Free-tier keys end with ":fx"
        self._endpoint = _API_FREE if api_key.endswith(":fx") else _API_PRO

    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> list[str]:
        headers = {"Authorization": f"DeepL-Auth-Key {self._api_key}"}
        payload = {
            "text": [text],
            "source_lang": source_lang.upper(),
            "target_lang": target_lang.upper(),
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._endpoint, headers=headers, json=payload
            )
        response.raise_for_status()
        return [t["text"] for t in response.json()["translations"] if t.get("text")]
