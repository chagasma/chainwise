interface TraceLineProps {
  active?: boolean;
  className?: string;
}

/** The signature motif: a glowing horizontal trace with a traveling pulse.
 * Reused as a divider, a connector between trace nodes, and the loading state. */
export function TraceLine({ active = false, className = "" }: TraceLineProps) {
  return (
    <div className={`relative h-px w-full overflow-hidden ${className}`}>
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(90deg, transparent, var(--color-cyan) 20%, var(--color-violet) 50%, var(--color-magenta) 80%, transparent)",
          opacity: active ? 0.9 : 0.35,
        }}
      />
      {active && (
        <div
          className="animate-scan absolute inset-y-0 w-1/3"
          style={{
            background:
              "linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent)",
          }}
        />
      )}
    </div>
  );
}
