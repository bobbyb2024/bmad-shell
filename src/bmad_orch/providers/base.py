import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from bmad_orch.types import OutputChunk


class ProviderAdapter(ABC):
    """Abstract Base Class for all provider adapters."""

    install_hint: str = "Install the CLI for this provider."

    @abstractmethod
    def detect(self, cli_path: str | None = None) -> bool:
        """Detect if the provider CLI binary is available on the system.
        
        Args:
            cli_path (str | None): Optional custom path/name to check.
        """
        pass

    @abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """List available models for this provider."""
        pass

    def _get_base_metadata(self, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN401
        """Provide base metadata including execution_id. AC4."""
        return {
            "execution_id": kwargs.get("execution_id", str(uuid.uuid4())),
            "timestamp": time.time()
        }

    async def execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:  # noqa: ANN401
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
    def _execute(self, prompt: str, **kwargs: Any) -> AsyncIterator[OutputChunk]:  # noqa: ANN401
        """Concrete implementation of prompt execution."""
        ...
