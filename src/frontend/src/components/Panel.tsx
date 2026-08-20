import type { ReactNode } from "react";

interface PanelProps {
  title?: ReactNode;
  eyebrow?: string;
  accent?: "cyan" | "magenta" | "violet" | "amber" | "neutral";
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const ACCENTS: Record<string, string> = {
  cyan: "var(--color-cyan)",
  magenta: "var(--color-magenta)",
  violet: "var(--color-violet)",
  amber: "var(--color-amber)",
  neutral: "var(--color-line)",
};

export function Panel({
  title,
  eyebrow,
  accent = "neutral",
  children,
  className = "",
  style,
}: PanelProps) {
  const accentColor = ACCENTS[accent];
  return (
    <section
      className={`animate-rise relative rounded-xl border p-5 backdrop-blur-sm ${className}`}
      style={{
        background: "rgba(16, 21, 42, 0.55)",
        borderColor: "var(--color-line)",
        boxShadow:
          accent !== "neutral" ? `0 0 0 1px rgba(255,255,255,0.02), 0 12px 40px -20px ${accentColor}` : undefined,
        ...style,
      }}
    >
      {accent !== "neutral" && (
        <div
          className="absolute top-0 left-5 h-px w-10 rounded-full"
          style={{ background: accentColor, boxShadow: `0 0 8px ${accentColor}` }}
        />
      )}
      {(eyebrow || title) && (
        <header className="mb-3.5 flex items-center justify-between gap-3">
          <div>
            {eyebrow && (
              <p
                className="font-mono text-[10px] font-semibold tracking-[0.18em] uppercase"
                style={{ color: accentColor === "var(--color-line)" ? "var(--color-text-dim)" : accentColor }}
              >
                {eyebrow}
              </p>
            )}
            {title && <h3 className="mt-0.5 font-display text-base font-semibold text-[var(--color-text)]">{title}</h3>}
          </div>
        </header>
      )}
      {children}
    </section>
  );
}
