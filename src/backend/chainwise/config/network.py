from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

NETWORKS_DIR = Path(__file__).parent / "networks"


class NetworkConfig(BaseModel):
    """A single network's connection and grounding config, loaded from YAML."""

    name: str
    chain_id: int
    explorer_url: str
    rpc_url: str
    repos: list[str]
    abi_strategy: list[Literal["explorer", "repo"]] = Field(
        default_factory=lambda: ["explorer", "repo"]
    )


@lru_cache
def load_network(network: str) -> NetworkConfig:
    path = NETWORKS_DIR / f"{network}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in NETWORKS_DIR.glob("*.yaml"))
        raise FileNotFoundError(f"Unknown network '{network}'. Available: {available}")
    data = yaml.safe_load(path.read_text())
    return NetworkConfig.model_validate(data)
