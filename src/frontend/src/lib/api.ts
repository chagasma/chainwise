// Mirrors src/backend/chainwise/api/schemas.py and models/domain.py.
// Keep in sync by hand — no codegen in this project.

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export type ExplanationMode = "developer" | "support" | "auditor";

export interface NetworkConfig {
  name: string;
  chain_id: number;
  explorer_url: string;
  rpc_url: string;
  repos: string[];
  abi_strategy: string[];
}

export interface DecodedParameter {
  name: string;
  type: string;
  value: unknown;
}

export interface DecodedInput {
  method_call: string;
  method_id: string;
  parameters: DecodedParameter[];
}

export interface LogEntry {
  address: string;
  event: string | null;
  decoded: Record<string, unknown> | null;
}

export interface TransactionSummary {
  hash: string;
  status: "success" | "reverted" | "pending";
  block_number: number | null;
  timestamp: string | null;
  from_address: string;
  to_address: string | null;
  value_wei: string;
  gas_used: number | null;
  fee_wei: string | null;
  method: string | null;
  decoded_input: DecodedInput | null;
  raw_input: string | null;
  revert_reason: string | null;
  logs: LogEntry[];
  source_url: string;
}

export interface TokenMetadata {
  address: string;
  symbol: string | null;
  decimals: number | null;
}

export interface DecodedCall {
  function: string;
  signature: string;
  parameters: Record<string, unknown>;
}

export interface RepoGroundingResult {
  repo: string;
  file_path: string;
  source_url: string;
  decoded_call: DecodedCall;
}

export interface SecurityFinding {
  pattern: string;
  severity: "high" | "medium" | "info";
  description: string;
  evidence: string;
}

export interface TransactionRelation {
  kind: string;
  description: string;
  tx_hashes: string[];
}

export interface LLMPromptPayload {
  summary: TransactionSummary;
  tokens: TokenMetadata[];
  grounding: RepoGroundingResult | null;
  security_findings: SecurityFinding[];
}

export interface ExplanationResponse extends LLMPromptPayload {
  explanation: string;
  needs_clarification: boolean;
  thread_id: string;
  mode: ExplanationMode;
  gas_tips: boolean;
}

export interface MultiTransactionAnalysisResponse {
  transactions: LLMPromptPayload[];
  relations: TransactionRelation[];
  explanation: string;
  thread_id: string;
  mode: ExplanationMode;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`);
  } catch {
    throw new ApiError(0, "Could not reach the ChainWise backend — is it running?");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.detail ?? `Request failed (${res.status}).`);
  }
  return res.json() as Promise<T>;
}

export function getNetwork(): Promise<NetworkConfig> {
  return request<NetworkConfig>("/network");
}

export function getTransaction(hash: string): Promise<TransactionSummary> {
  return request<TransactionSummary>(`/tx/${hash}`);
}

export function explainTransaction(
  hash: string,
  mode: ExplanationMode,
  gasTips: boolean,
): Promise<ExplanationResponse> {
  const params = new URLSearchParams({ mode, gas_tips: String(gasTips) });
  return request<ExplanationResponse>(`/tx/${hash}/explain?${params}`);
}

export function analyzeTransactions(
  hashes: string[],
  mode: ExplanationMode,
): Promise<MultiTransactionAnalysisResponse> {
  const params = new URLSearchParams({ mode });
  for (const h of hashes) params.append("hash", h);
  return request<MultiTransactionAnalysisResponse>(`/analyze?${params}`);
}
