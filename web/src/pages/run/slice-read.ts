// Shared by the slice readers: a failure names its path and the first one wins.
export type Bar = { label: string; value: number; max: number }; // numbers place the fill only
export class Invalid extends Error {}
export const fail = (path: string, expected: string): never => {
  throw new Invalid(`${path}: expected ${expected}`);
};
export type Obj = Record<string, unknown>;

export function obj(v: unknown, path: string): Obj {
  if (typeof v !== "object" || v === null || Array.isArray(v)) return fail(path, "an object");
  return v as Obj;
}
// A module code (CP-3) stays off these pages: every string is checked where it is read.
const noCode = (v: string, at: string): string =>
  /\bCP-\d/.test(v) ? fail(at, "no module code") : v;
export function str(o: Obj, key: string, path: string): string {
  const v = o[key];
  return typeof v === "string" ? noCode(v, `${path}.${key}`) : fail(`${path}.${key}`, "a string");
}
// A file name is the analyst's own (it may read CP-1.pdf); it is the one string with no check.
export function fileName(o: Obj, key: string, path: string): string {
  const v = o[key];
  return typeof v === "string" ? v : fail(`${path}.${key}`, "a string");
}
export function strOrNull(o: Obj, key: string, path: string): string | null {
  const v = o[key];
  if (v === null) return v;
  return typeof v === "string"
    ? noCode(v, `${path}.${key}`)
    : fail(`${path}.${key}`, "a string or null");
}
const ID = /^[a-z0-9-]+$/;
const idWords = "an id of lower-case letters, digits and hyphens";
export function id(o: Obj, key: string, path: string): string {
  const v = str(o, key, path);
  return ID.test(v) ? v : fail(`${path}.${key}`, idWords);
}
export function idOrNull(o: Obj, key: string, path: string): string | null {
  const v = strOrNull(o, key, path);
  return v === null || ID.test(v) ? v : fail(`${path}.${key}`, idWords);
}
export function nonEmpty<T>(items: T[], path: string): T[] {
  return items.length === 0 ? fail(path, "a non-empty list") : items;
}
export function list<T>(
  o: Obj,
  key: string,
  path: string,
  read: (v: unknown, p: string) => T,
): T[] {
  const v = o[key];
  if (!Array.isArray(v)) return fail(`${path}.${key}`, "a list");
  return v.map((item, i) => read(item, `${path}.${key}[${String(i)}]`));
}
export function oneOf<T extends string>(o: Obj, key: string, path: string, words: readonly T[]): T {
  const v = o[key];
  return words.find((w) => w === v) ?? fail(`${path}.${key}`, `one of ${words.join(", ")}`);
}
export function bar(v: unknown, path: string): Bar {
  const o = obj(v, path);
  const label = str(o, "label", path);
  const { value, max } = o;
  if (typeof max !== "number" || !Number.isFinite(max) || max <= 0)
    fail(`${path}.max`, "a number above 0");
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    value < 0 ||
    value > (max as number)
  ) {
    fail(`${path}.value`, "a number from 0 to max");
  }
  return { label, value: value as number, max: max as number };
}
export function orNull<T>(
  o: Obj,
  key: string,
  path: string,
  read: (v: unknown, p: string) => T,
): T | null {
  const v = o[key];
  if (v === null) return null;
  if (typeof v !== "object" || Array.isArray(v)) return fail(`${path}.${key}`, "an object or null");
  return read(v, `${path}.${key}`);
}
export const strings = (o: Obj, key: string, path: string): string[] =>
  list(o, key, path, (v, p) => (typeof v === "string" ? noCode(v, p) : fail(p, "a string")));
