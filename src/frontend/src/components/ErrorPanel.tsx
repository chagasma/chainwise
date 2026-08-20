import { Panel } from "./Panel";

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className="mx-auto w-full max-w-3xl px-6 sm:px-0">
      <Panel eyebrow="Trace failed" accent="magenta">
        <p className="font-mono text-sm text-[var(--color-text)]">{message}</p>
      </Panel>
    </div>
  );
}
