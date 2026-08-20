import type { TransactionSummary } from "../lib/api";
import { Panel } from "./Panel";
import { StatusPill } from "./StatusPill";
import { TxTracePath } from "./TxTracePath";
import { formatTimestamp, weiToEth } from "../lib/format";

function Field({ label, value, mono = true }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="font-mono text-[10px] tracking-widest text-[var(--color-text-faint)] uppercase">{label}</dt>
      <dd className={`mt-0.5 truncate text-sm ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

export function SummaryCard({ summary }: { summary: TransactionSummary }) {
  return (
    <Panel eyebrow="Transaction" accent="cyan">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <a
          href={summary.source_url}
          target="_blank"
          rel="noreferrer"
          className="font-mono text-sm text-[var(--color-text)] hover:text-[var(--color-cyan)]"
        >
          {summary.hash}
        </a>
        <StatusPill status={summary.status} />
      </div>

      <div className="mb-4">
        <TxTracePath summary={summary} />
      </div>

      {summary.revert_reason && (
        <p className="mb-4 rounded-md border border-[var(--color-magenta)] bg-[rgba(255,46,136,0.08)] px-3 py-2 font-mono text-xs text-[var(--color-magenta)]">
          revert: {summary.revert_reason}
        </p>
      )}

      <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
        <Field label="Block" value={summary.block_number ?? "pending"} />
        <Field label="Timestamp" value={formatTimestamp(summary.timestamp)} mono={false} />
        <Field label="Value" value={`${weiToEth(summary.value_wei)} native`} />
        <Field label="Gas used" value={summary.gas_used?.toLocaleString() ?? "—"} />
        <Field label="From" value={summary.from_address} />
        <Field label="To" value={summary.to_address ?? "(contract creation)"} />
        <Field label="Fee" value={summary.fee_wei ? `${weiToEth(summary.fee_wei)} native` : "—"} />
        <Field label="Method" value={summary.method ?? "unknown"} />
      </dl>
    </Panel>
  );
}
