import type { ExplanationMode } from "../lib/api";

const MODES: { value: ExplanationMode; label: string; hint: string }[] = [
  { value: "developer", label: "Developer", hint: "calls, params, gas — technical detail" },
  { value: "support", label: "Support", hint: "plain language, no jargon" },
  { value: "auditor", label: "Auditor", hint: "flags sensitive patterns explicitly" },
];

export function ModeSelector({
  value,
  onChange,
}: {
  value: ExplanationMode;
  onChange: (m: ExplanationMode) => void;
}) {
  return (
    <div role="radiogroup" aria-label="Explanation audience" className="flex flex-wrap gap-1.5">
      {MODES.map((m) => {
        const active = value === m.value;
        return (
          <button
            key={m.value}
            type="button"
            role="radio"
            aria-checked={active}
            title={m.hint}
            onClick={() => onChange(m.value)}
            className="rounded-lg border px-3 py-1.5 font-mono text-xs font-medium transition-colors"
            style={{
              borderColor: active ? "var(--color-cyan)" : "var(--color-line)",
              color: active ? "var(--color-cyan)" : "var(--color-text-dim)",
              background: active ? "rgba(0,240,255,0.08)" : "transparent",
            }}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
