"""A small on-disk cache that saves repeated local model requests."""

import hashlib
import json
from pathlib import Path
from typing import Any

from mcp_tdo.agents.models import ProviderResponse


class ResponseCache:
    """Store responses by the complete request that produced them."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def key(
        self, model: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int
    ) -> str:
        """Build a stable filename for one exact model request."""
        request = json.dumps(
            {"model": model, "messages": messages, "tools": tools, "seed": seed},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(request.encode("utf-8")).hexdigest()

    def get(self, key: str) -> ProviderResponse | None:
        """Read a response if it is already cached."""
        path = self.directory / f"{key}.json"
        if not path.exists():
            return None
        return ProviderResponse.model_validate_json(path.read_text(encoding="utf-8"))

    def put(self, key: str, response: ProviderResponse) -> None:
        """Save a response so the next identical request can skip the model."""
        path = self.directory / f"{key}.json"
        path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
