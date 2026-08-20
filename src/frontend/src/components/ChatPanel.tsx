import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ApiError, sendChatMessage, type ExplanationMode } from "../lib/api";
import { CopyButton } from "./CopyButton";
import { ExplanationPanel } from "./ExplanationPanel";

interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

interface ChatPanelProps {
  threadId: string;
  explanation: string;
  mode: ExplanationMode;
  gasTips?: boolean;
  needsClarification?: boolean;
  title?: string;
}

export function ChatPanel({
  threadId,
  explanation,
  mode,
  gasTips,
  needsClarification,
  title,
}: ChatPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || sending) return;

    setInput("");
    setError(null);
    setTurns((prev) => [...prev, { role: "user", content: message }]);
    setSending(true);
    try {
      const res = await sendChatMessage(threadId, message);
      setTurns((prev) => [...prev, { role: "assistant", content: res.reply }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't send that — try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <ExplanationPanel
        explanation={explanation}
        mode={mode}
        gasTips={gasTips}
        needsClarification={needsClarification}
        title={title}
      />

      {turns.length > 0 && (
        <div className="flex max-h-[50vh] flex-col gap-3 overflow-y-auto rounded-xl border border-[var(--color-line)] bg-[rgba(16,21,42,0.4)] p-4">
          {turns.map((turn, i) =>
            turn.role === "user" ? (
              <div key={i} className="ml-8 rounded-lg bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text)]">
                {turn.content}
              </div>
            ) : (
              <div key={i} className="mr-8 space-y-1">
                <div className="prose-chainwise text-sm leading-relaxed text-[var(--color-text)]">
                  <ReactMarkdown>{turn.content}</ReactMarkdown>
                </div>
                <CopyButton text={turn.content} />
              </div>
            ),
          )}
        </div>
      )}

      <form onSubmit={handleSend} className="mt-auto flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a follow-up question…"
          disabled={sending}
          className="flex-1 rounded-lg border border-[var(--color-line)] bg-[var(--color-surface)]/70 px-3 py-2 text-sm text-[var(--color-text)] outline-none placeholder:text-[var(--color-text-faint)] focus:shadow-[0_0_0_1px_var(--color-cyan)]"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-lg border border-[var(--color-cyan)] px-4 py-2 font-mono text-xs font-semibold tracking-wide text-[var(--color-cyan)] uppercase transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
        >
          {sending ? "…" : "Send"}
        </button>
      </form>
      {error && <p className="font-mono text-xs text-[var(--color-magenta)]">{error}</p>}
    </div>
  );
}
