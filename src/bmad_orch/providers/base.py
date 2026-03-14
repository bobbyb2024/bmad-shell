from abc import ABC, abstractmethod
from typing import AsyncIterator, Any
import uuid
import time
from dataclasses import replace
from bmad_orch.types import OutputChunk


class ProviderAdapter(ABC):
    """Abstract Base Class for all provider adapters."""

    install_hint: str = "Install the CLI for this provider."

    @abstractmethod
    def detect(self) -> bool:
        """Detect if the provider CLI binary is available on the system."""
        pass

    @abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """List available models for this provider."""
        pass

    def _get_base_metadata(self, **kwargs: Any) -> dict[str, Any]:
        """Provide base metadata including execution_id. AC4."""
        return {
            "execution_id": kwargs.get("execution_id", str(uuid.uuid4())),
            "timestamp": time.time()
        }

    async def execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        """Execute the prompt and stream output chunks."""
        # Ensure a unique execution_id per execute() call
        base_meta = self._get_base_metadata(**kwargs)
        
        async for chunk in self._execute(prompt, **kwargs):
            # Attach execution_id if missing in metadata
            if "execution_id" not in chunk.metadata:
                new_metadata = {**base_meta, **chunk.metadata}
                chunk = replace(chunk, metadata=new_metadata)
            yield chunk

    @abstractmethod
    async def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:
        """Concrete implementation of prompt execution."""
        pass
