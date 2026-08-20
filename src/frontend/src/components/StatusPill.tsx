const STYLES: Record<string, { label: string; color: string; glow: string }> = {
  success: { label: "Success", color: "var(--color-cyan)", glow: "rgba(0,240,255,0.35)" },
  reverted: { label: "Reverted", color: "var(--color-magenta)", glow: "rgba(255,46,136,0.35)" },
  pending: { label: "Pending", color: "var(--color-amber)", glow: "rgba(255,176,32,0.35)" },
};

export function StatusPill({ status }: { status: string }) {
  const s = STYLES[status] ?? STYLES.pending;
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-xs font-medium tracking-wide uppercase"
      style={{
        color: s.color,
        borderColor: s.color,
        background: s.glow,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />
      {s.label}
    </span>
  );
}
