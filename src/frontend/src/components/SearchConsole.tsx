import { useState } from "react";
import type { ExplanationMode } from "../lib/api";
import { ModeSelector } from "./ModeSelector";
import { Toggle } from "./Toggle";
import { TraceLine } from "./TraceLine";

export type QueryMode = "single" | "multi";

interface SearchConsoleProps {
  queryMode: QueryMode;
  onQueryModeChange: (m: QueryMode) => void;
  explanationMode: ExplanationMode;
  onExplanationModeChange: (m: ExplanationMode) => void;
  gasTips: boolean;
  onGasTipsChange: (v: boolean) => void;
  loading: boolean;
  onSubmit: (hashes: string[]) => void;
}

const HASH_RE = /^0x[0-9a-fA-F]{64}$/;

export function SearchConsole({
  queryMode,
  onQueryModeChange,
  explanationMode,
  onExplanationModeChange,
  gasTips,
  onGasTipsChange,
  loading,
  onSubmit,
}: SearchConsoleProps) {
  const [hashes, setHashes] = useState<string[]>([""]);
  const [touched, setTouched] = useState(false);

  const needed = queryMode === "multi" ? 2 : 1;
  while (hashes.length < needed) hashes.push("");

  function setHash(i: number, v: string) {
    const next = [...hashes];
    next[i] = v;
    setHashes(next);
  }

  function addHash() {
    setHashes([...hashes, ""]);
  }

  function removeHash(i: number) {
    setHashes(hashes.filter((_, idx) => idx !== i));
  }

  const trimmed = hashes.map((h) => h.trim()).filter(Boolean);
  const invalid = trimmed.some((h) => !HASH_RE.test(h));
  const enough = trimmed.length >= needed;
  const canSubmit = enough && !invalid && !loading;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!canSubmit) return;
    onSubmit(trimmed);
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-6 sm:px-0">
      <p className="font-mono text-xs tracking-[0.3em] text-[var(--color-cyan)] uppercase">
        network-agnostic transaction assistant
      </p>
      <h1 className="mt-3 font-display text-4xl leading-[1.05] font-semibold tracking-tight sm:text-5xl">
        Trace any transaction.
        <br />
        <span
          style={{
            background: "linear-gradient(90deg, var(--color-cyan), var(--color-violet) 55%, var(--color-magenta))",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          Plain language, grounded in fact.
        </span>
      </h1>
      <p className="mt-4 max-w-xl text-sm text-[var(--color-text-dim)]">
        Paste a transaction hash. ChainWise reads the explorer, the chain, and the contract's own
        source to explain what happened — citing everything it used.
      </p>

      <div className="mt-2">
        <TraceLine active={loading} className="mt-8" />
      </div>

      <form onSubmit={handleSubmit} className="mt-6">
        <div className="mb-3 flex gap-1.5">
          {(["single", "multi"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => onQueryModeChange(m)}
              className="rounded-md px-2.5 py-1 font-mono text-[11px] font-semibold tracking-wide uppercase transition-colors"
              style={{
                color: queryMode === m ? "var(--color-text)" : "var(--color-text-faint)",
                borderBottom: queryMode === m ? "2px solid var(--color-magenta)" : "2px solid transparent",
              }}
            >
              {m === "single" ? "Single transaction" : "Multi-transaction analysis"}
            </button>
          ))}
        </div>

        <div className="space-y-2">
          {hashes.slice(0, queryMode === "single" ? 1 : hashes.length).map((h, i) => {
            const isInvalid = touched && h.trim() && !HASH_RE.test(h.trim());
            return (
              <div key={i} className="flex items-center gap-2">
                <div
                  className="group relative flex flex-1 items-center rounded-lg border bg-[var(--color-surface)]/70 px-4 py-3 backdrop-blur-sm transition-shadow focus-within:shadow-[0_0_0_1px_var(--color-cyan),0_0_24px_-8px_var(--color-cyan)]"
                  style={{ borderColor: isInvalid ? "var(--color-magenta)" : "var(--color-line)" }}
                >
                  <span className="mr-2 select-none font-mono text-sm text-[var(--color-text-faint)]">0x</span>
                  <input
                    value={h.replace(/^0x/, "")}
                    onChange={(e) => setHash(i, "0x" + e.target.value.replace(/^0x/, ""))}
                    placeholder="a1b2c3…64 hex chars"
                    spellCheck={false}
                    autoComplete="off"
                    className="w-full bg-transparent font-mono text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-faint)]"
                  />
                </div>
                {queryMode === "multi" && hashes.length > 2 && (
                  <button
                    type="button"
                    onClick={() => removeHash(i)}
                    aria-label="Remove this transaction"
                    className="rounded-md border border-[var(--color-line)] px-2 py-2 text-[var(--color-text-faint)] hover:text-[var(--color-magenta)]"
                  >
                    ✕
                  </button>
                )}
              </div>
            );
          })}
        </div>
        {touched && invalid && (
          <p className="mt-2 font-mono text-xs text-[var(--color-magenta)]">
            each hash needs to be 0x followed by 64 hex characters.
          </p>
        )}

        {queryMode === "multi" && (
          <button
            type="button"
            onClick={addHash}
            className="mt-2 font-mono text-xs text-[var(--color-cyan)] hover:underline"
          >
            + add another transaction
          </button>
        )}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <ModeSelector value={explanationMode} onChange={onExplanationModeChange} />
          {queryMode === "single" && <Toggle checked={gasTips} onChange={onGasTipsChange} label="gas tips" />}
        </div>

        <button
          type="submit"
          disabled={!canSubmit}
          className="mt-5 w-full rounded-lg border py-3 font-display text-sm font-semibold tracking-wide uppercase transition-all disabled:cursor-not-allowed disabled:opacity-40"
          style={{
            borderColor: "var(--color-cyan)",
            color: "var(--color-void)",
            background: "linear-gradient(90deg, var(--color-cyan), var(--color-violet))",
            boxShadow: canSubmit ? "0 8px 30px -10px var(--color-cyan)" : undefined,
          }}
        >
          {loading ? "Tracing…" : queryMode === "single" ? "Trace transaction" : "Trace & compare"}
        </button>
      </form>
    </div>
  );
}
