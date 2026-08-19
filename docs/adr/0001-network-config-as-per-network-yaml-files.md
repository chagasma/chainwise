# 1. Network config as one YAML file per network

## Status

Accepted

## Context

ChainWise must be network-agnostic: retargeting from one EVM network to another
(e.g. Ethereum mainnet → CloudWalk private) must be possible by editing
configuration only, no code changes. Each network needs: an explorer base URL
(Blockscout-compatible), an RPC URL, one or more GitHub repos for contract
grounding, and an ABI resolution strategy (explorer first, repo fallback).

Three formats were considered:

1. **A single `config/networks.yaml`** registering every network under one
   root key, with an env var selecting the active one.
2. **One `.env` file per network** (`.env.mainnet`, `.env.cloudwalk`),
   reusing the `pydantic-settings` mechanism already used for app config.
3. **One YAML file per network**, under `config/networks/<name>.yaml`, with
   an env var (`CHAINWISE_NETWORK`) naming the active file.

Option 1 grows into a single shared file that every new network has to be
added to, producing noisy diffs and merge conflicts. Option 2 is awkward for
structured fields (a list of repos, an ordered ABI strategy) — env vars want
flat scalars, not lists.

## Decision

Use option 3: one YAML file per network in `config/networks/`, loaded and
validated through a `NetworkConfig` pydantic model. `Settings.network`
(env `CHAINWISE_NETWORK`) selects which file to load. Adding a network means
adding one new file — no existing file is touched, and no code changes.

## Consequences

- Adding/removing a network never touches another network's file, keeping
  diffs and code review scoped to the network being changed.
- `NetworkConfig` gives schema validation (pydantic) instead of hand-rolled
  YAML parsing per adapter.
- Slightly more files than a single registry, but each is small and
  self-contained — considered a feature here, not a cost.
- We ship 3 real networks (Ethereum mainnet, Gnosis Chain, Polygon PoS) from
  the start specifically to prove the format is actually network-agnostic,
  not just designed to look that way for a single network.
