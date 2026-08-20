const STYLES: Record<string, { color: string; bg: string }> = {
  high: { color: "#ff2e88", bg: "rgba(255,46,136,0.12)" },
  medium: { color: "#ffb020", bg: "rgba(255,176,32,0.12)" },
  info: { color: "#00f0ff", bg: "rgba(0,240,255,0.12)" },
};

export function SeverityBadge({ severity }: { severity: string }) {
  const s = STYLES[severity] ?? STYLES.info;
  return (
    <span
      className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-widest uppercase"
      style={{ color: s.color, borderColor: s.color, background: s.bg }}
    >
      {severity}
    </span>
  );
}
