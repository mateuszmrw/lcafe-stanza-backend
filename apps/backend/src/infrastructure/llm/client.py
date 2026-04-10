from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract interface for LLM providers used by grammar explanation."""

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the assistant response text."""
        ...
