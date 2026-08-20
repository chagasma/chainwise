import { useEffect, useState } from "react";
import {
  ApiError,
  analyzeTransactions,
  explainTransaction,
  getNetwork,
  type ExplanationMode,
  type ExplanationResponse,
  type MultiTransactionAnalysisResponse,
  type NetworkConfig,
} from "./lib/api";
import { TopBar } from "./components/TopBar";
import { SearchConsole, type QueryMode } from "./components/SearchConsole";
import { LoadingTrace } from "./components/LoadingTrace";
import { ErrorPanel } from "./components/ErrorPanel";
import { SummaryCard } from "./components/SummaryCard";
import { TokensList, SecurityFindings } from "./components/TokensAndSecurity";
import { GroundingCitation } from "./components/GroundingCitation";
import { ExplanationPanel } from "./components/ExplanationPanel";
import { MultiTxView } from "./components/MultiTxView";

type Result =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "single"; data: ExplanationResponse }
  | { kind: "multi"; data: MultiTransactionAnalysisResponse };

function App() {
  const [network, setNetwork] = useState<NetworkConfig | null>(null);
  const [networkError, setNetworkError] = useState(false);
  const [queryMode, setQueryMode] = useState<QueryMode>("single");
  const [explanationMode, setExplanationMode] = useState<ExplanationMode>("developer");
  const [gasTips, setGasTips] = useState(false);
  const [result, setResult] = useState<Result>({ kind: "idle" });

  useEffect(() => {
    getNetwork()
      .then(setNetwork)
      .catch(() => setNetworkError(true));
  }, []);

  async function handleSubmit(hashes: string[]) {
    setResult({ kind: "loading" });
    try {
      if (hashes.length === 1) {
        const data = await explainTransaction(hashes[0], explanationMode, gasTips);
        setResult({ kind: "single", data });
      } else {
        const data = await analyzeTransactions(hashes, explanationMode);
        setResult({ kind: "multi", data });
      }
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Something went wrong tracing that.";
      setResult({ kind: "error", message });
    }
  }

  return (
    <div className="min-h-screen pb-24">
      <TopBar network={network} error={networkError} />

      <main className="mt-4 flex flex-col gap-12">
        <SearchConsole
          queryMode={queryMode}
          onQueryModeChange={setQueryMode}
          explanationMode={explanationMode}
          onExplanationModeChange={setExplanationMode}
          gasTips={gasTips}
          onGasTipsChange={setGasTips}
          loading={result.kind === "loading"}
          onSubmit={handleSubmit}
        />

        {result.kind === "loading" && <LoadingTrace />}
        {result.kind === "error" && <ErrorPanel message={result.message} />}

        {result.kind === "single" && (
          <div className="mx-auto w-full max-w-5xl px-6 sm:px-0">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <SummaryCard summary={result.data.summary} />
                <ExplanationPanel
                  explanation={result.data.explanation}
                  mode={result.data.mode}
                  gasTips={result.data.gas_tips}
                  needsClarification={result.data.needs_clarification}
                />
              </div>
              <div className="space-y-4">
                <SecurityFindings findings={result.data.security_findings} />
                <TokensList tokens={result.data.tokens} />
                <GroundingCitation grounding={result.data.grounding} />
              </div>
            </div>
          </div>
        )}

        {result.kind === "multi" && (
          <div className="mx-auto w-full max-w-5xl px-6 sm:px-0">
            <MultiTxView result={result.data} />
          </div>
        )}
      </main>

      <footer className="mx-auto mt-20 w-full max-w-5xl px-6 text-center font-mono text-[11px] text-[var(--color-text-faint)] sm:px-0">
        ChainWise reads {network?.name ?? "the configured network"} through a Blockscout-compatible
        explorer, an RPC endpoint, and {network?.repos.length ?? 0} configured source repo
        {network && network.repos.length !== 1 ? "s" : ""}. Switching networks is a config change,
        not a code change.
      </footer>
    </div>
  );
}

export default App;
