import type { RepoGroundingResult } from "../lib/api";
import { Panel } from "./Panel";

export function GroundingCitation({ grounding }: { grounding: RepoGroundingResult | null }) {
  if (!grounding) return null;
  return (
    <Panel eyebrow="Repo grounding" accent="amber">
      <p className="mb-2 text-xs text-[var(--color-text-dim)]">
        Explorer had no ABI for this call — decoded against a matched artifact in the network's
        configured source repo.
      </p>
      <a
        href={grounding.source_url}
        target="_blank"
        rel="noreferrer"
        className="block truncate font-mono text-xs text-[var(--color-amber)] hover:underline"
      >
        {grounding.repo} → {grounding.file_path}
      </a>
      <p className="mt-2 font-mono text-xs">
        <span className="text-[var(--color-text)]">{grounding.decoded_call.function}</span>
        <span className="text-[var(--color-text-faint)]"> — {grounding.decoded_call.signature}</span>
      </p>
    </Panel>
  );
}
