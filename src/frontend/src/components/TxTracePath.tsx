import type { TransactionSummary } from "../lib/api";
import { shortHash } from "../lib/format";

function Node({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent: string;
}) {
  return (
    <div
      className="flex min-w-0 shrink-0 flex-col rounded-lg border px-3 py-2"
      style={{ borderColor: accent, background: "var(--color-surface)" }}
    >
      <span className="font-mono text-[9px] tracking-widest text-[var(--color-text-faint)] uppercase">{label}</span>
      <span className="max-w-40 truncate font-mono text-xs" style={{ color: accent }} title={value}>
        {value}
      </span>
    </div>
  );
}

function Connector() {
  return (
    <div className="flex w-6 shrink-0 items-center justify-center sm:w-8">
      <div
        className="h-px w-full"
        style={{ background: "linear-gradient(90deg, var(--color-cyan), var(--color-magenta))", opacity: 0.5 }}
      />
    </div>
  );
}

/** The signature motif applied to a single transaction: its own call path,
 * from sender through the decoded call to whatever events fired. */
export function TxTracePath({ summary }: { summary: TransactionSummary }) {
  const method = summary.decoded_input?.method_call?.split("(")[0] ?? summary.method ?? "transfer";
  const events = summary.logs.filter((l) => l.event).map((l) => l.event!.split("(")[0]);

  return (
    <div className="scrollbar-none flex items-center overflow-x-auto pb-1">
      <Node label="from" value={shortHash(summary.from_address)} accent="var(--color-cyan)" />
      <Connector />
      <Node
        label={summary.to_address ? "call" : "contract creation"}
        value={method}
        accent="var(--color-violet)"
      />
      {events.length > 0 ? (
        events.slice(0, 4).map((ev, i) => (
          <span key={i} className="flex items-center">
            <Connector />
            <Node label="event" value={ev} accent="var(--color-magenta)" />
          </span>
        ))
      ) : (
        <span className="flex items-center">
          <Connector />
          <Node label="events" value="none emitted" accent="var(--color-text-faint)" />
        </span>
      )}
    </div>
  );
}
