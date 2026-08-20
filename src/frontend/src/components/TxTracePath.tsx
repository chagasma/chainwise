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
      className="flex min-w-0 items-center justify-between gap-3 rounded-lg border px-3 py-1.5"
      style={{ borderColor: accent, background: "var(--color-surface)" }}
    >
      <span className="shrink-0 font-mono text-[9px] tracking-widest text-[var(--color-text-faint)] uppercase">
        {label}
      </span>
      <span className="truncate font-mono text-xs" style={{ color: accent }} title={value}>
        {value}
      </span>
    </div>
  );
}

function Connector() {
  return (
    <div className="flex h-2.5 justify-start pl-5">
      <div
        className="w-px"
        style={{ background: "linear-gradient(180deg, var(--color-cyan), var(--color-magenta))", opacity: 0.5 }}
      />
    </div>
  );
}

/** The signature motif applied to a single transaction: its own call path,
 * from sender through the decoded call to whatever events fired. Stacked
 * vertically (not a horizontal scroller) so it reads cleanly in a narrow
 * column. */
export function TxTracePath({ summary }: { summary: TransactionSummary }) {
  const method = summary.decoded_input?.method_call?.split("(")[0] ?? summary.method ?? "transfer";
  const events = summary.logs.filter((l) => l.event).map((l) => l.event!.split("(")[0]);

  return (
    <div className="flex flex-col">
      <Node label="from" value={shortHash(summary.from_address)} accent="var(--color-cyan)" />
      <Connector />
      <Node
        label={summary.to_address ? "call" : "contract creation"}
        value={method}
        accent="var(--color-violet)"
      />
      {events.length > 0 ? (
        events.slice(0, 4).map((ev, i) => (
          <div key={i}>
            <Connector />
            <Node label="event" value={ev} accent="var(--color-magenta)" />
          </div>
        ))
      ) : (
        <div>
          <Connector />
          <Node label="events" value="none emitted" accent="var(--color-text-faint)" />
        </div>
      )}
    </div>
  );
}
