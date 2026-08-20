export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 font-mono text-xs font-medium text-[var(--color-text-dim)]"
    >
      <span
        className="relative inline-flex h-5 w-9 items-center rounded-full border transition-colors"
        style={{
          borderColor: checked ? "var(--color-amber)" : "var(--color-line)",
          background: checked ? "rgba(255,176,32,0.15)" : "transparent",
        }}
      >
        <span
          className="inline-block h-3.5 w-3.5 transform rounded-full transition-transform"
          style={{
            background: checked ? "var(--color-amber)" : "var(--color-text-faint)",
            boxShadow: checked ? "0 0 6px var(--color-amber)" : undefined,
            transform: checked ? "translateX(18px)" : "translateX(3px)",
          }}
        />
      </span>
      <span style={{ color: checked ? "var(--color-amber)" : undefined }}>{label}</span>
    </button>
  );
}
