import pytest
import asyncio
from bmad_orch.providers import ProviderAdapter
from bmad_orch.types import OutputChunk
from typing import AsyncIterator, Any
import time


def test_provider_adapter_abc_enforcement():
    # Attempting to instantiate ABC directly or subclass without methods should fail
    with pytest.raises(TypeError):
        ProviderAdapter()

    class IncompleteProvider(ProviderAdapter):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_mock_provider_execution_id():
    import uuid

    class RealMockProvider(ProviderAdapter):
        def detect(self): return True
        def list_models(self): return []
        async def _execute(self, prompt, **kwargs):
            # No manual execution_id generation here
            yield OutputChunk(content="test", timestamp=time.time(), metadata={})

    async def run_test():
        provider = RealMockProvider()
        chunks = []
        async for chunk in provider.execute("test", execution_id="fixed-id"):
            chunks.append(chunk)
        
        assert chunks[0].metadata["execution_id"] == "fixed-id"

        chunks = []
        async for chunk in provider.execute("test"):
            chunks.append(chunk)
        assert "execution_id" in chunks[0].metadata
        assert isinstance(uuid.UUID(chunks[0].metadata["execution_id"]), uuid.UUID)

    asyncio.run(run_test())
