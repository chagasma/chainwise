# 1.4 AnyChain Transaction Assistant

## Link: https://www.cloudwalk.io/nimbus

## Goal

Build a configurable AI assistant that explains and troubleshoots EVM transactions and Solidity smart contracts. The tool must be network-agnostic: it should work on any EVM network (e.g., Ethereum mainnet) and be re-targetable to another network (e.g., CloudWalk private) by changing configuration only (no code changes).

## Tasks

- **Transaction explainer**
  - Input a transaction hash and return a clear summary of what happened (calls, value transfers, emitted events).
- **Failure diagnostics**
  - If the transaction failed/reverted, return a diagnosis, likely root causes, and actionable next steps.
- **Explorer integration (Blockscout-compatible)**
  - Fetch tx/receipt/logs (and contract metadata when available) from a configurable Blockscout explorer API.
- **On-chain context via read calls**
  - Use a configurable RPC endpoint to perform read-only calls (eth_call) to gather contract state needed for context.
- **Smart contract repo grounding**
  - Use one or more configured smart contract repositories (GitHub) to explain contract/function behavior and provide relevant security notes.
- **Simple interface**
  - Provide a minimal UI (web preferred) or CLI + local API server.

## Requirements

- **Configuration-driven portability**
  - Switching networks must be possible by editing config only.
  - Config must include:
    - explorer base URL (Blockscout-compatible)
    - RPC URL
    - one or more repo URLs
    - ABI/decoding strategy: prefer explorer ABI, fallback to repo artifacts/ABIs, otherwise degrade gracefully
- **Grounded answers**
  - Include citations/links to sources used (explorer links/endpoints, repo paths/commits, docs).
- **Graceful degradation**
  - If ABI/RPC/explorer data is missing/unavailable, clearly state uncertainty and what's needed to proceed.
- **Lightweight & deployable**
  - Must run locally. Provide clear run instructions.
- **README**
  - Include setup + configuration example + at least 3 sample conversations (or example queries/outputs).

## Bonus Features

- Structured triage flow (asks clarifying questions before concluding)
- Modes (developer / support / auditor)
- Multi-transaction analysis (trace related transactions)
- Gas optimization suggestions
- Security vulnerability detection based on known patterns
