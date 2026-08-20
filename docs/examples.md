# Examples

Real requests and real responses, run against Ethereum mainnet through the live backend. Every
hash below is a real transaction. Nothing here is made up or mocked. Amounts, gas numbers and
addresses may differ if you run these again later, since some responses depend on the live
Blockscout API.

## 1. A simple explain (developer mode)

The default case. A hash comes in, the explorer already has the ABI, and the model explains it in
full.

Request:

```
GET /tx/0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5/explain
```

Response (`explanation` field):

```
Here's what this transaction did, in plain terms.

What happened
- Contract call: transfer(address to, uint256 value) on the USDC ERC-20 contract at 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48.
- Sender: 0x834800A69ac51cb6E48272228b6b8a41742Ff8ec.
- Recipient (transfer target): 0x59238C30e17a5E4Dd2F921159d3A7f209eFa30B9.
- Ether value moved: none (value_wei = 0).

Decoded input details
- Method: transfer(address to, uint256 value)
- Method ID: a9059cbb
- Parameters:
    - to = 0x59238C30e17a5E4Dd2F921159d3A7f209eFa30B9
    - value = 500000000 (in base ERC-20 units)

What was emitted in logs
- ERC-20 Transfer event on USDC:
    - from: 0x834800A69ac51cb6E48272228b6b8a41742Ff8ec
    - to: 0x59238C30e17a5E4Dd2F921159d3A7f209eFa30B9
    - value: 500000000 (base units)

Token context
- Token involved: USDC (address 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48)
- Symbol: USDC
- Decimals: 6
- Amount in human terms: 500000000 base units / 10^6 = 500.0 USDC

Transaction metadata
- Status: success
- Block: 25798689
- Timestamp: 2026-08-20T20:21:23Z
- Gas used: 40,348
- Fee paid (in wei): 4,862,217,686,788
- Estimated fee (in ETH): ~0.0048622 ETH
- Source of data: https://eth.blockscout.com/tx/0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5
```

This covers the two required core features at once: the transaction explainer and grounded
answers (the source URL and the decoded ABI fields are the actual evidence, not an assumption).

## 2. Structured triage, then a follow up in chat

Some contracts aren't verified on the explorer and aren't in any configured repo. ChainWise does
not guess what an undecoded call does. It states what it knows for sure and asks one specific
question.

Request:

```
GET /tx/0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5/explain
```

Response (`needs_clarification: true`, `explanation` field):

```
1) What is known for certain
- Status: success
- Transaction hash: 0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5
- From: 0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97
- To (contract): 0xFEEEEEE44046c3f61a8CC081E0918eF0de0a7ffC
- Block: 25798677, Timestamp: 2026-08-20T20:18:59Z
- Value sent: 6735887103870423 wei (~0.006735887103870423 ETH)
- Gas used: 29022, Fee: 2857042609638 wei
- Decoded input: null (no ABI available in explorer for decoding)
- Method selector: 0x6a876133
- Logs: none
- Tokens: none
- Source URL: https://eth.blockscout.com/tx/0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5

One clarifying question
Do you have the ABI for this contract (or know which repository/branch contains its source) so I
can decode the input and explain the call?
```

The response also returns a `thread_id`. Use it to reply in the same conversation:

Request:

```
POST /chat
{
  "thread_id": "0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5",
  "message": "Here is the ABI for method 0x6a876133: function claimSmoothingPoolShare(bytes32 poolId) external. It claims this address's share of accumulated MEV rewards from the smoothing pool. Please explain the transaction now."
}
```

Response (`reply` field):

```
1) What is known for certain now
- Transaction: 0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5 (success)
- From: 0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97
- To (contract): 0xFEEEEEE44046c3f61a8CC081E0918eF0de0a7ffC
- Block/Timestamp: 25798677, 2026-08-20T20:18:59Z
- Value sent: 6,735,887,103,870,423 wei (~0.006735887103870423 ETH)
- Gas used: 29,022; Fee: 2,857,042,609,638 wei (~0.002857 ETH)
- Method: claimSmoothingPoolShare(bytes32 poolId)
- Decoded input: now decoded with the ABI you provided
    - poolId (32 byte, left padded): 0x000000000000000000000000000000000000000000000000e688b84b23f322a994a53dbf8e15fa82cdb71127
    - Short form: poolId = 0xE688B84B23F322A994A53DBF8E15FA82CDB71127 (with 12 leading zero bytes in the full 32 byte word)
- Purpose of call: to claim this address's share of accumulated MEV rewards from the smoothing pool
- Logs: none emitted in this transaction
- Source: https://eth.blockscout.com/tx/0xff6f79a9720abf41f693249ea1875b21e10f929a8618b9aa80e579897a0b1fa5

2) One clarifying question
Would you like me to check the post transaction balances (your address or the contract) and any
subsequent state changes to verify the exact reward credited by this claim?
```

This shows three things at once: the structured triage flow refusing to guess, grounded answers
staying grounded even in a follow up, and the conversational chat actually using the new
information the user gave it instead of repeating "I don't know."

## 3. A reverted transaction (failure diagnostics)

Request:

```
GET /tx/0x99c92a339bd94cc478b8a25f8d3f0aff6db69c4f16da05feabdede49384a6240/explain
```

Response (`summary.status: "reverted"`, `explanation` field, shortened):

```
1) What was attempted
- Contract and method: transferFrom(address _from, address _to, uint256 _value) on the USDT contract.
- Initiator and intent: sent from 0xA26148AE51fa8E787DF319C04137602Cc018b521, calling transferFrom
  to move tokens from 0xe9ff19AbCdFE2D1afF7D2E0A6e57022d6E77ed14 to itself.
- Amount: 1,168,314,578 base units.
- Result: the call reverted. No revert_reason was provided by the explorer. No Transfer events
  were emitted.

2) Likely root cause
- No revert reason was given, so the following are inferred, not confirmed, from typical ERC-20
  behavior:
    - Insufficient allowance: the caller may not have enough allowance from the owner.
    - Insufficient balance: the owner may not hold enough of the token.
    - Token specific restrictions: the contract may have a paused state, a blacklist, or other
      checks not visible from this data alone.

3) Next steps
- Check allowance(_from, spender) to confirm the spender has enough approved.
- Check balanceOf(_from) to confirm the owner has enough balance.
- Query decimals() and symbol() to read the amount in human terms.
- Review the contract's transferFrom implementation for non-standard require conditions.
```

The full response also includes `security_findings: []`, confirming the deterministic
pattern check ran and found nothing, not that it was skipped.

## 4. Multi transaction analysis

Two transactions from the same sender, analyzed together.

Request:

```
GET /analyze?hash=0xbf56a2ada8495d72b1c43063e5b84e2d22840156a647eb1e9f3a01c8a3319ef3&hash=0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5
```

Response (`relations` field):

```
[
  {
    "kind": "shared_sender",
    "description": "All sent from the same address: 0x834800A69ac51cb6E48272228b6b8a41742Ff8ec.",
    "tx_hashes": [
      "0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5",
      "0xbf56a2ada8495d72b1c43063e5b84e2d22840156a647eb1e9f3a01c8a3319ef3"
    ]
  }
]
```

Response (`explanation` field, shortened):

```
1. Each transaction

- Transaction 1: A USDC transfer of 500 USDC from 0x8348...Ff8ec to 0x5923...a30B9.
  Source: https://eth.blockscout.com/tx/0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5

- Transaction 2: A plain ETH transfer from the same sender to the same recipient, about
  0.02077 ETH, no logs, no method input.
  Source: https://eth.blockscout.com/tx/0xbf56a2ada8495d72b1c43063e5b84e2d22840156a647eb1e9f3a01c8a3319ef3

2. How they relate

The shared_sender relation above is a confirmed fact, not a guess: both transactions came from
0x834800A69ac51cb6E48272228b6b8a41742Ff8ec. They also went to the same recipient address, which is
an additional observation worth noting as a reading of the data rather than a matched pattern.
```

`relations` are computed deterministically before the transactions ever reach the model. The model
is instructed to relay them as fact and clearly label anything beyond that as its own reading.

## 5. Auditor mode

Same explainer, different audience. The `mode` query parameter changes tone and what gets called
out, not the underlying data.

Request:

```
GET /tx/0x8ad2ac392922310aeabf739613da1f728fe4204ef212314c402eded54853f9c1/explain?mode=auditor
```

Response (`explanation` field, shortened):

```
Summary of the transaction
- A successful approve call to the USDT contract by owner 0x4C8193c3F28EeDb9d833e81cBEf8dEfD670B524A.
- Function called: approve(address _spender, uint256 _value)
- Spender approved: 0x111111125421cA6dc452d289314280a0f8842A65
- Approved value: 1,705,870,870 base units
- ERC-20 event Approval confirms the grant.

What happened, in plain terms
- The owner granted the spender an allowance on USDT. No tokens moved, only the allowance
  changed.

Security review
- security_findings is empty: no known risky pattern (unlimited approval, ownership transfer,
  and so on) matched here. The approved amount is finite, not the max uint256 value that would
  flag as an unlimited approval.
```

For a transaction where the approved value is the maximum uint256, `security_findings` comes back
with an `unlimited-approval` entry instead of an empty list, and the model is instructed to relay
it as a pre-computed fact rather than something to double-check.

## 6. Support mode with gas tips

Non-technical language, plus an extra section comparing gas used to typical ranges.

Request:

```
GET /tx/0x00e01f7bbf89b25c00133a974a17c612ebf603b53612c824e2626e331d9619e5/explain?mode=support&gas_tips=true
```

Response (`explanation` field):

```
Here's a plain language summary of the transaction.

What happened
- Your address 0x834800A69ac51cb6E48272228b6b8a41742Ff8ec called the USDC contract to transfer
  500 USDC to 0x59238C30e17a5E4Dd2F921159d3A7f209eFa30B9.

What was transferred
- Amount: 500 USDC.

Gas and fee
- Gas used: 40,348
- Fee paid: about 0.004862 ETH

Gas efficiency
- Operation: standard ERC-20 transfer (USDC)
- Typical gas range: roughly 45,000 to 65,000
- This transaction used 40,348 gas, a bit lower than usual for this kind of transfer. Not
  anomalous. Since the transfer succeeded, there is no revert path to evaluate for efficiency.
```

## Switching networks

All of the examples above ran against `ethereum-mainnet`, the default. Switching
`CHAINWISE_NETWORK` to `polygon-pos` or `gnosis-chain` (or a new network you add a YAML file for)
points the whole pipeline, explorer, RPC, and repo grounding, at the new network with no code
change. This was validated live against all three networks during development, see
`docs/planning.md` section 0 for the details, including a real portability issue found and fixed
along the way (Gnosis Chain's documented Blockscout URL had been discontinued in favor of a
differently named but API compatible host).
