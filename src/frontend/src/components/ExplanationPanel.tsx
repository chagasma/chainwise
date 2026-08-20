import ReactMarkdown from "react-markdown";
import type { ExplanationMode } from "../lib/api";
import { CopyButton } from "./CopyButton";
import { Panel } from "./Panel";

interface ExplanationPanelProps {
  explanation: string;
  mode: ExplanationMode;
  gasTips?: boolean;
  needsClarification?: boolean;
  title?: string;
}

export function ExplanationPanel({
  explanation,
  mode,
  gasTips,
  needsClarification,
  title = "Explanation",
}: ExplanationPanelProps) {
  const accent = needsClarification ? "violet" : "cyan";
  return (
    <Panel
      accent={accent}
      eyebrow={needsClarification ? "Needs clarification" : "Explanation"}
      title={
        <span className="flex flex-wrap items-center gap-2">
          {title}
          <span className="rounded border border-[var(--color-line)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-dim)] uppercase">
            {mode}
          </span>
          {gasTips && (
            <span className="rounded border border-[var(--color-amber)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-amber)] uppercase">
              gas tips
            </span>
          )}
        </span>
      }
      actions={<CopyButton text={explanation} />}
    >
      {needsClarification && (
        <p className="mb-3 rounded-md border border-[var(--color-violet)] bg-[rgba(124,92,255,0.08)] px-3 py-2 font-mono text-xs text-[var(--color-violet)]">
          ChainWise couldn't decode this call from the explorer or any configured repo — read
          below for the one question it needs answered before it can go further.
        </p>
      )}
      <div className="prose-chainwise text-sm leading-relaxed text-[var(--color-text)]">
        <ReactMarkdown>{explanation}</ReactMarkdown>
      </div>
    </Panel>
  );
}
