export function shortHash(hash: string, size = 6): string {
  if (hash.length <= size * 2 + 2) return hash;
  return `${hash.slice(0, size + 2)}…${hash.slice(-size)}`;
}

export function weiToEth(wei: string, maxFractionDigits = 6): string {
  const value = BigInt(wei);
  const negative = value < 0n;
  const abs = negative ? -value : value;
  const whole = abs / 10n ** 18n;
  const frac = (abs % 10n ** 18n).toString().padStart(18, "0").slice(0, maxFractionDigits);
  const trimmed = frac.replace(/0+$/, "");
  const sign = negative ? "-" : "";
  return trimmed ? `${sign}${whole}.${trimmed}` : `${sign}${whole}`;
}

export function formatTimestamp(ts: string | null): string {
  if (!ts) return "unknown time";
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) return ts;
  return date.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function tokenAmount(rawValue: unknown, decimals: number | null): string {
  const raw = String(rawValue ?? "0");
  if (decimals === null || !/^\d+$/.test(raw)) return raw;
  if (decimals === 18) return weiToEth(raw);
  const value = BigInt(raw);
  const base = 10n ** BigInt(decimals);
  const whole = value / base;
  const frac = (value % base).toString().padStart(decimals, "0").slice(0, 6).replace(/0+$/, "");
  return frac ? `${whole}.${frac}` : `${whole}`;
}
