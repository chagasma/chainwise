import type { SecurityFinding, TokenMetadata } from "../lib/api";
import { Panel } from "./Panel";
import { SeverityBadge } from "./SeverityBadge";
import { shortHash } from "../lib/format";

export function TokensList({ tokens }: { tokens: TokenMetadata[] }) {
  if (tokens.length === 0) return null;
  return (
    <Panel eyebrow="Tokens involved" accent="violet">
      <ul className="space-y-2">
        {tokens.map((t) => (
          <li key={t.address} className="flex items-center justify-between font-mono text-sm">
            <span className="font-semibold text-[var(--color-violet)]">{t.symbol ?? "unknown"}</span>
            <span className="text-[var(--color-text-faint)]">
              {t.decimals ?? "?"} decimals · {shortHash(t.address)}
            </span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function SecurityFindings({ findings }: { findings: SecurityFinding[] }) {
  if (findings.length === 0) {
    return (
      <Panel eyebrow="Security" accent="neutral">
        <p className="font-mono text-xs text-[var(--color-text-dim)]">
          no known risky pattern matched against this call.
        </p>
      </Panel>
    );
  }
  return (
    <Panel eyebrow="Security findings" accent="magenta">
      <ul className="space-y-3">
        {findings.map((f, i) => (
          <li key={i} className="border-l-2 border-[var(--color-magenta)] pl-3">
            <div className="flex items-center gap-2">
              <SeverityBadge severity={f.severity} />
              <span className="font-mono text-xs font-semibold text-[var(--color-text)]">{f.pattern}</span>
            </div>
            <p className="mt-1 text-xs text-[var(--color-text-dim)]">{f.description}</p>
            <p className="mt-1 font-mono text-[11px] text-[var(--color-text-faint)]">{f.evidence}</p>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
