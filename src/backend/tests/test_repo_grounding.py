import base64
import json

import httpx
from chainwise.adapters import GitHubClient
from chainwise.config import NetworkConfig
from chainwise.services.decoder import function_selector
from chainwise.services.repo_grounding import ground_transaction

REPO_URL = "https://github.com/example/contracts"
REPO_SLUG = "example/contracts"

NETWORK = NetworkConfig(
    name="test",
    chain_id=1,
    explorer_url="https://explorer.example",
    rpc_url="https://rpc.example",
    repos=(REPO_URL,),
)

TRANSFER_ABI = [
    {
        "type": "function",
        "name": "transfer",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
        ],
        "stateMutability": "nonpayable",
    }
]

RAW_INPUT = (
    function_selector("transfer(address,uint256)")
    + "0" * 24
    + "1" * 40
    + "0" * 62
    + "0a"
)


def _b64(obj: object) -> str:
    return base64.b64encode(json.dumps(obj).encode()).decode()


def _patch_github(monkeypatch, handler: httpx.MockTransport) -> None:
    monkeypatch.setattr(
        "chainwise.services.repo_grounding.GitHubClient",
        lambda token=None: GitHubClient(token=token, transport=handler),
    )


def _search_then_contents(search_items: list[dict], contents_by_path: dict[str, dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/code":
            return httpx.Response(200, json={"items": search_items})
        path = request.url.path.removeprefix(f"/repos/{REPO_SLUG}/contents/")
        if path in contents_by_path:
            return httpx.Response(200, json=contents_by_path[path])
        return httpx.Response(404, json={})

    return httpx.MockTransport(handler)


def test_ground_transaction_returns_none_without_repos() -> None:
    network = NetworkConfig(**{**NETWORK.model_dump(), "repos": []})
    assert ground_transaction(RAW_INPUT, network) is None


def test_ground_transaction_returns_none_for_empty_input() -> None:
    assert ground_transaction(None, NETWORK) is None
    assert ground_transaction("0x", NETWORK) is None


def test_ground_transaction_finds_and_decodes_matching_artifact(monkeypatch) -> None:
    transport = _search_then_contents(
        search_items=[{"path": "artifacts/Token.json"}],
        contents_by_path={
            "artifacts/Token.json": {
                "content": _b64({"abi": TRANSFER_ABI}),
                "encoding": "base64",
            }
        },
    )
    _patch_github(monkeypatch, transport)

    result = ground_transaction(RAW_INPUT, NETWORK)

    assert result is not None
    assert result.repo == REPO_SLUG
    assert result.file_path == "artifacts/Token.json"
    assert result.source_url == f"https://github.com/{REPO_SLUG}/blob/HEAD/artifacts/Token.json"
    assert result.decoded_call.function == "transfer"


def test_ground_transaction_skips_files_with_no_matching_function(monkeypatch) -> None:
    other_abi = [{"type": "function", "name": "approve", "inputs": []}]
    transport = _search_then_contents(
        search_items=[{"path": "artifacts/Other.json"}],
        contents_by_path={
            "artifacts/Other.json": {"content": _b64({"abi": other_abi}), "encoding": "base64"}
        },
    )
    _patch_github(monkeypatch, transport)

    assert ground_transaction(RAW_INPUT, NETWORK) is None


def test_ground_transaction_skips_malformed_json(monkeypatch) -> None:
    transport = _search_then_contents(
        search_items=[{"path": "artifacts/Broken.json"}],
        contents_by_path={
            "artifacts/Broken.json": {
                "content": base64.b64encode(b"not json").decode(),
                "encoding": "base64",
            }
        },
    )
    _patch_github(monkeypatch, transport)

    assert ground_transaction(RAW_INPUT, NETWORK) is None


def test_ground_transaction_skips_non_abi_json(monkeypatch) -> None:
    """A JSON file that happens to match the search query but isn't an ABI/artifact."""
    transport = _search_then_contents(
        search_items=[{"path": "package.json"}],
        contents_by_path={
            "package.json": {
                "content": _b64({"name": "contracts", "version": "1.0.0"}),
                "encoding": "base64",
            }
        },
    )
    _patch_github(monkeypatch, transport)

    assert ground_transaction(RAW_INPUT, NETWORK) is None


def test_ground_transaction_accepts_bare_abi_array(monkeypatch) -> None:
    """Some repos publish the ABI array directly, not wrapped in a Truffle/Hardhat artifact."""
    transport = _search_then_contents(
        search_items=[{"path": "abi/Token.json"}],
        contents_by_path={
            "abi/Token.json": {"content": _b64(TRANSFER_ABI), "encoding": "base64"}
        },
    )
    _patch_github(monkeypatch, transport)

    result = ground_transaction(RAW_INPUT, NETWORK)

    assert result is not None
    assert result.decoded_call.function == "transfer"


def test_ground_transaction_reads_solc_combined_json_with_multiple_contracts(monkeypatch) -> None:
    """`solc --combined-json abi` output: several contracts' ABIs in one file, keyed by
    "file.sol:ContractName" — must try each one, not just the first."""
    combined = {
        "contracts": {
            "Other.sol:Other": {"abi": [{"type": "function", "name": "approve", "inputs": []}]},
            "Token.sol:Token": {"abi": TRANSFER_ABI},
        },
        "version": "0.8.20+commit.deadbeef",
    }
    transport = _search_then_contents(
        search_items=[{"path": "build/combined-abi.json"}],
        contents_by_path={
            "build/combined-abi.json": {"content": _b64(combined), "encoding": "base64"}
        },
    )
    _patch_github(monkeypatch, transport)

    result = ground_transaction(RAW_INPUT, NETWORK)

    assert result is not None
    assert result.file_path == "build/combined-abi.json"
    assert result.decoded_call.function == "transfer"


def test_ground_transaction_degrades_gracefully_when_search_fails(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    _patch_github(monkeypatch, httpx.MockTransport(handler))

    assert ground_transaction(RAW_INPUT, NETWORK) is None


def test_ground_transaction_degrades_gracefully_when_rate_limited(monkeypatch, caplog) -> None:
    """Common without GITHUB_TOKEN configured — must not be logged as a real failure."""
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={})
    )
    _patch_github(monkeypatch, transport)

    with caplog.at_level("WARNING", logger="chainwise.repo_grounding"):
        result = ground_transaction(RAW_INPUT, NETWORK)

    assert result is None
    assert not any("repo_search_failed" in r.message for r in caplog.records)


def test_ground_transaction_tries_next_repo_after_a_failure(monkeypatch) -> None:
    network = NetworkConfig(
        **{**NETWORK.model_dump(), "repos": ["https://github.com/broken/repo", REPO_URL]}
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if "repo:broken/repo" in request.url.params.get("q", ""):
            return httpx.Response(503, json={})
        if request.url.path == "/search/code":
            return httpx.Response(200, json={"items": [{"path": "artifacts/Token.json"}]})
        return httpx.Response(
            200,
            json={"content": _b64({"abi": TRANSFER_ABI}), "encoding": "base64"},
        )

    _patch_github(monkeypatch, httpx.MockTransport(handler))

    result = ground_transaction(RAW_INPUT, network)

    assert result is not None
    assert result.repo == REPO_SLUG
