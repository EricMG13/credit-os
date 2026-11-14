import { readFileSync } from "node:fs";
import path from "node:path";

/** A fresh copy of the model fixture's slice, read from disk. */
export function fixtureSlice(): unknown {
  const file = path.resolve(import.meta.dirname, "..", "..", "..", "..", "fixtures", "model.json");
  return (JSON.parse(readFileSync(file, "utf8")) as { slice: unknown }).slice;
}

/** The copy with the value at `steps` replaced, or the key removed when `value` is `undefined`. */
export function edited(steps: readonly (string | number)[], value: unknown): unknown {
  if (steps.length === 0) return value;
  const slice = fixtureSlice();
  let at = slice as Record<string | number, unknown>;
  for (const step of steps.slice(0, -1)) at = at[step] as Record<string | number, unknown>;
  const last = steps[steps.length - 1] as string | number;
  if (value === undefined) Reflect.deleteProperty(at, last);
  else at[last] = value;
  return slice;
}

/** The value, or a thrown error when a query found nothing. */
export function must<T>(value: T | null | undefined): T {
  if (value === null || value === undefined) throw new Error("expected a value, found none");
  return value;
}
