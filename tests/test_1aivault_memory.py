from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


agent_module = types.ModuleType("agent")
memory_provider_module = types.ModuleType("agent.memory_provider")
memory_provider_module.MemoryProvider = object
sys.modules.setdefault("agent", agent_module)
sys.modules.setdefault("agent.memory_provider", memory_provider_module)

MODULE = Path(__file__).parents[1] / "__init__.py"
spec = importlib.util.spec_from_file_location("one_aivault_memory_test", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeClient:
    def __init__(self):
        self.calls = []

    def call(self, name, args):
        self.calls.append((name, args))
        if name == "vault_search":
            return {"content": [{"type": "text", "text": '{"results":[{"title":"Shared note","snippet":"Use project notes as source of truth."}]}'}]}
        return {"ok": True}

    def close(self):
        pass


provider = module.OneAIVaultMemoryProvider()
provider._client = FakeClient()
provider.is_available = lambda: True
assert module._redact("api_key=dummy-value-1234") == "[REDACTED]"
assert provider.prefetch("Project notes source of truth") == "- Shared note: Use project notes as source of truth."
provider.on_memory_write("add", "memory", "Keep shared notes usable by Claude Code and Codex.")
name, args = provider._client.calls[-1]
assert name == "vault_save"
assert "agent:claude-code" in args["tags"]
assert "agent:codex" in args["tags"]
print("1aivault-memory self-check: OK")
