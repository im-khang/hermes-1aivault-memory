from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path


agent_module = types.ModuleType("agent")
memory_provider_module = types.ModuleType("agent.memory_provider")
memory_provider_module.MemoryProvider = object
redact_module = types.ModuleType("agent.redact")


def redact_sensitive_text(text, *, force=False, code_file=False):
    return re.sub(r"(?i)(api[_-]?key\s*[:=]\s*)\S+", r"\1«redacted-secret»", text)


redact_module.redact_sensitive_text = redact_sensitive_text
sys.modules.setdefault("agent", agent_module)
sys.modules.setdefault("agent.memory_provider", memory_provider_module)
sys.modules.setdefault("agent.redact", redact_module)

MODULE = Path(__file__).parents[1] / "__init__.py"
spec = importlib.util.spec_from_file_location("one_aivault_memory_test", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeClient:
    def __init__(self):
        self.calls = []

    def start(self):
        pass

    def call(self, name, args):
        self.calls.append((name, args))
        if name == "vault_search":
            if args.get("response_format") == "detailed":
                payload = {"results": [{"id": "entry-1", "tags": ["shared-memory"]}]}
            else:
                payload = {"results": [{"title": "Shared note", "snippet": "Use project notes as source of truth."}]}
            return {"content": [{"type": "text", "text": json.dumps(payload)}]}
        if name == "vault_get":
            payload = {
                "id": "entry-1",
                "content": "  old   shared\nfact  ",
                "tags": ["shared-memory"],
            }
            return {"content": [{"type": "text", "text": json.dumps(payload)}]}
        return {"content": [{"type": "text", "text": '{"success":true}'}]}

    def close(self):
        pass


provider = module.OneAIVaultMemoryProvider()
provider._client = FakeClient()
provider.is_available = lambda: True
provider.initialize("test", agent_identity="Work Profile")
assert provider._profile_tag == "hermes-profile:work-profile"

assert module._redact("api_key=dummy-value-1234") == "api_key=[REDACTED]"
assert module._redact("api_key=opaque-secret") == "api_key=[REDACTED]"
assert module._redact("password: opaque-secret") == "password: [REDACTED]"
assert module._redact("TOKEN=opaque-secret") == "TOKEN=[REDACTED]"
assert module._redact("Bearer opaque-token") == "Bearer [REDACTED]"
assert "[REDACTED]" in module._redact("AKIA" + "A" * 16)
assert "[REDACTED]" in module._redact("glpat-" + "a" * 16)
assert "[REDACTED]" in module._redact("eyJ" + "a" * 12 + "." + "b" * 8)
assert "[REDACTED]" in module._redact("https://user:password@example.com")
assert "[REDACTED]" in module._redact("https://example.com/?access_token=opaque")
assert "[REDACTED]" in module._redact(
    "-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----"
)

assert provider.prefetch("Project notes source of truth") == "- Shared note: Use project notes as source of truth."

provider.on_memory_write("add", "memory", "new shared fact")
name, args = provider._client.calls[-1]
assert name == "vault_save"
assert "agent:claude-code" in args["tags"]
assert "agent:codex" in args["tags"]
assert "hermes-profile:work-profile" in args["tags"]

provider.on_memory_write("replace", "memory", "new shared fact", {"old_text": "old shared fact"})
assert provider._client.calls[-1][0] == "vault_update"
assert provider._client.calls[-1][1]["id"] == "entry-1"

provider.on_memory_write("remove", "memory", "", {"old_text": "old shared fact"})
assert provider._client.calls[-1] == (
    "vault_forget_entry",
    {"id": "entry-1", "reason": "Removed from Hermes built-in memory"},
)

provider._client.calls.clear()
provider.on_memory_write("remove", "memory", "", {"old_text": "old shared"})
assert all(name != "vault_forget_entry" for name, _ in provider._client.calls)

print("1aivault-memory self-check: OK")
