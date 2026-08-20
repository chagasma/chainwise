import type { NetworkConfig } from "../lib/api";

export function TopBar({ network, error }: { network: NetworkConfig | null; error: boolean }) {
  return (
    <header className="flex items-center justify-between px-6 py-5 sm:px-10">
      <div className="flex items-center gap-2.5">
        <svg width="22" height="22" viewBox="0 0 32 32" aria-hidden>
          <path
            d="M6 22 L12 22 L15 10 L18 24 L21 16 L26 16"
            fill="none"
            stroke="url(#tb-grad)"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <defs>
            <linearGradient id="tb-grad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#00f0ff" />
              <stop offset="1" stopColor="#ff2e88" />
            </linearGradient>
          </defs>
        </svg>
        <span className="font-display text-lg font-semibold tracking-tight">ChainWise</span>
      </div>

      {error ? (
        <span className="rounded-full border border-[var(--color-magenta)] px-3 py-1 font-mono text-xs text-[var(--color-magenta)]">
          backend unreachable
        </span>
      ) : network ? (
        <div className="flex items-center gap-2 rounded-full border border-[var(--color-line)] bg-[var(--color-surface)]/60 px-3 py-1.5 font-mono text-xs text-[var(--color-text-dim)]">
          <span className="animate-pulse-glow h-1.5 w-1.5 rounded-full bg-[var(--color-cyan)]" />
          <span className="text-[var(--color-text)]">{network.name}</span>
          <span className="text-[var(--color-text-faint)]">·</span>
          <span>chain {network.chain_id}</span>
        </div>
      ) : (
        <span className="font-mono text-xs text-[var(--color-text-faint)]">connecting…</span>
      )}
    </header>
  );
}
