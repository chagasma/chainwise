import { TraceLine } from "./TraceLine";

const STEPS = ["reading explorer", "resolving token metadata", "checking repo grounding", "asking the model"];

export function LoadingTrace() {
  return (
    <div className="animate-rise mx-auto w-full max-w-3xl px-6 py-10 sm:px-0">
      <TraceLine active />
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className="animate-pulse-glow font-mono text-xs text-[var(--color-text-dim)]"
            style={{ animationDelay: `${i * 0.2}s` }}
          >
            {s}…
          </span>
        ))}
      </div>
    </div>
  );
}
