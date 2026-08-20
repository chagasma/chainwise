import json
from typing import Any
from urllib.parse import urlparse

from chainwise.adapters import GitHubClient, GitHubError
from chainwise.config import NetworkConfig
from chainwise.models import RepoGroundingResult
from chainwise.observability import get_logger
from chainwise.services.decoder import decode_function_input

logger = get_logger("chainwise.repo_grounding")

# Compiled ABI artifacts (Truffle/Hardhat/Foundry) all serialize each ABI
# entry's "stateMutability" field; plain source or unrelated JSON rarely
# contains that exact string, so it's a solid low-noise search filter.
_ARTIFACT_SEARCH_QUERY = '"stateMutability" extension:json'
_MAX_CANDIDATES_PER_REPO = 5


def _repo_slug(repo_url: str) -> str:
    """"https://github.com/owner/name(.git)" -> "owner/name"."""
    return urlparse(repo_url).path.strip("/").removesuffix(".git")


def _extract_abis(data: Any) -> list[list[dict[str, Any]]]:
    """Finds every ABI array in a JSON file, whatever build tool produced it.

    Handles three shapes seen in the wild:
    - a bare ABI array,
    - a Truffle/Hardhat/Foundry artifact ({"abi": [...], ...other build metadata}),
    - a solc `--combined-json abi` file ({"contracts": {"file.sol:Name": {"abi": [...]}}}),
      which can hold several contracts' worth of ABI in one file.
    """
    if isinstance(data, list) and all(isinstance(entry, dict) for entry in data):
        return [data]
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("abi"), list):
        return [data["abi"]]
    if isinstance(data.get("contracts"), dict):
        return [
            contract["abi"]
            for contract in data["contracts"].values()
            if isinstance(contract, dict) and isinstance(contract.get("abi"), list)
        ]
    return []


def ground_transaction(
    raw_input: str | None, network: NetworkConfig, github_token: str = ""
) -> RepoGroundingResult | None:
    """Best-effort ABI-fallback grounding: decode `raw_input` against an artifact
    found in one of `network.repos`, for use when the explorer had no ABI to decode it.

    Every failure mode (repo unreachable, rate-limited, file isn't valid JSON,
    no function in the artifact matches) is non-fatal: it just means this
    repo/file isn't the source, so the search moves on. Returns None rather
    than raising when nothing matches anywhere.
    """
    if not raw_input or raw_input == "0x" or not network.repos:
        return None

    with GitHubClient(token=github_token or None) as github:
        for repo_url in network.repos:
            repo = _repo_slug(repo_url)
            try:
                candidates = github.search_code(repo, _ARTIFACT_SEARCH_QUERY)
            except GitHubError as exc:
                logger.warning("repo_search_failed", extra={"repo": repo, "error": str(exc)})
                continue

            for item in candidates[:_MAX_CANDIDATES_PER_REPO]:
                path = item.get("path")
                if not path:
                    continue
                result = _try_decode_against_file(github, repo, path, raw_input)
                if result is not None:
                    return result
    return None


def _try_decode_against_file(
    github: GitHubClient, repo: str, path: str, raw_input: str
) -> RepoGroundingResult | None:
    try:
        content = github.get_file_content(repo, path)
        abis = _extract_abis(json.loads(content))
    except (GitHubError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning(
            "repo_artifact_unreadable", extra={"repo": repo, "path": path, "error": str(exc)}
        )
        return None

    for abi in abis:
        decoded = decode_function_input(raw_input, abi)
        if decoded is not None:
            return RepoGroundingResult(
                repo=repo,
                file_path=path,
                source_url=f"https://github.com/{repo}/blob/HEAD/{path}",
                decoded_call=decoded,
            )
    return None
