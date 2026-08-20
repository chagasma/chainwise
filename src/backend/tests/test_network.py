import pytest
from chainwise.config import load_network


@pytest.mark.parametrize(
    "network",
    ["ethereum-mainnet", "gnosis-chain", "polygon-pos"],
)
def test_load_network_returns_valid_config(network: str) -> None:
    config = load_network(network)

    assert config.explorer_url.startswith("https://")
    assert config.rpc_url.startswith("https://")
    assert config.repos
    assert config.abi_strategy == ("explorer", "repo")


def test_load_network_raises_for_unknown_network() -> None:
    with pytest.raises(FileNotFoundError, match="Unknown network"):
        load_network("does-not-exist")
