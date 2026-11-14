/** The page groups, each owning one optional member of the data file. */
export const SLICE_KEYS = ["library", "model", "run", "signal"] as const;
export type SliceKey = (typeof SLICE_KEYS)[number];

/** A group's member is whatever the data file held, unread: the group's own reader checks it. */
export type LibraryData = {
  schema: "credit-os-data/1";
  issuers: readonly { id: string; name: string }[];
} & { [Key in SliceKey]?: unknown };

export type LoadResult =
  { kind: "ok"; data: LibraryData } | { kind: "missing" } | { kind: "newer"; schema: string };

declare global {
  interface Window {
    CREDIT_OS_DATA?: unknown;
  }
}

const KNOWN_SCHEMA = "credit-os-data/1";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readIssuers(value: unknown): LibraryData["issuers"] | undefined {
  if (!Array.isArray(value)) return undefined;
  const issuers: { id: string; name: string }[] = [];
  for (const item of value as unknown[]) {
    if (!isRecord(item) || typeof item["id"] !== "string" || typeof item["name"] !== "string") {
      return undefined;
    }
    issuers.push({ id: item["id"], name: item["name"] });
  }
  return issuers;
}

export function readLibraryData(source: unknown): LoadResult {
  if (!isRecord(source) || typeof source["schema"] !== "string") return { kind: "missing" };
  if (source["schema"] !== KNOWN_SCHEMA) return { kind: "newer", schema: source["schema"] };
  const issuers = readIssuers(source["issuers"]);
  if (issuers === undefined) return { kind: "missing" };
  const data: LibraryData = { schema: KNOWN_SCHEMA, issuers };
  for (const key of SLICE_KEYS) {
    if (Object.hasOwn(source, key) && source[key] !== undefined) data[key] = source[key];
  }
  return { kind: "ok", data };
}
