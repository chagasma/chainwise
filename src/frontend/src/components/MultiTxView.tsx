import type { MultiTransactionAnalysisResponse } from "../lib/api";
import { Panel } from "./Panel";
import { SummaryCard } from "./SummaryCard";
import { TokensList, SecurityFindings } from "./TokensAndSecurity";
import { GroundingCitation } from "./GroundingCitation";
import { ExplanationPanel } from "./ExplanationPanel";
import { shortHash } from "../lib/format";

const RELATION_ICON: Record<string, string> = {
  shared_sender: "↳",
  shared_counterparty: "⇄",
};

export function MultiTxView({ result }: { result: MultiTransactionAnalysisResponse }) {
  return (
    <div className="space-y-6">
      {result.relations.length > 0 && (
        <Panel eyebrow="Detected relations" accent="violet">
          <ul className="space-y-2">
            {result.relations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 font-mono text-xs">
                <span className="text-[var(--color-violet)]">{RELATION_ICON[r.kind] ?? "•"}</span>
                <span className="text-[var(--color-text-dim)]">
                  {r.description}{" "}
                  <span className="text-[var(--color-text-faint)]">
                    ({r.tx_hashes.map((h) => shortHash(h, 4)).join(", ")})
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <ExplanationPanel
        explanation={result.explanation}
        mode={result.mode}
        title="Combined analysis"
      />

      <div className="space-y-4">
        <p className="font-mono text-[10px] tracking-widest text-[var(--color-text-faint)] uppercase">
          {result.transactions.length} transactions, chronological order
        </p>
        {result.transactions.map((payload) => (
          <div key={payload.summary.hash} className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <SummaryCard summary={payload.summary} />
            </div>
            <div className="space-y-4">
              <SecurityFindings findings={payload.security_findings} />
              <TokensList tokens={payload.tokens} />
              <GroundingCitation grounding={payload.grounding} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
