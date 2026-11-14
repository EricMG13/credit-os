/** A reader checks one value at `path` and returns it typed, or throws a SliceError. */
export type Reader<T> = (value: unknown, path: string) => T;

/** The first failing path of a slice that does not match its type. */
export class SliceError extends Error {}

export const child = (path: string, key: string): string => (path === "" ? key : `${path}.${key}`);

export function fail(path: string, what: string): never {
  throw new SliceError(`${path}: ${what}`);
}
/** A string that may be empty: a chart's subtitle or note, which draws nothing when empty. */
const freeText: Reader<string> = (value, path) =>
  typeof value === "string" ? value : fail(path, "expected a string");

/** A string that holds something: a label drawn as text is never empty or only whitespace. */
export const text: Reader<string> = (value, path) => {
  if (typeof value !== "string") return fail(path, "expected a string");
  return value.trim() !== "" ? value : fail(path, "expected a non-empty string");
};

export const textOrNull: Reader<string | null> = (value, path) => {
  if (value === null) return null;
  if (typeof value !== "string") return fail(path, "expected a string or null");
  return value.trim() !== "" ? value : fail(path, "expected a non-empty string or null");
};

const inLibrary = (address: string, path: string): string =>
  address.startsWith("#/") ? address : fail(path, 'expected an address starting with "#/"');

/** An address into the library (a route, as the run group's reader requires): it starts with `#/`. */
export const address: Reader<string> = (value, path) => inLibrary(text(value, path), path);

/** An address into the library, or `null` where no control is drawn. */
export const addressOrNull: Reader<string | null> = (value, path) => {
  const read = textOrNull(value, path);
  return read === null ? null : inLibrary(read, path);
};

export const num: Reader<number> = (value, path) =>
  typeof value === "number" && Number.isFinite(value) ? value : fail(path, "expected a number");

export const numOrNull: Reader<number | null> = (value, path) =>
  value === null ? null : num(value, path);

export function pairOf<T>(item: Reader<T>): Reader<[T, T]> {
  const list = arrayOf(item);
  return (value, path) => {
    const [first, second, ...more] = list(value, path);
    if (first === undefined || second === undefined || more.length > 0) {
      return fail(path, "expected 2 entries");
    }
    return [first, second];
  };
}

export const bool: Reader<boolean> = (value, path) =>
  typeof value === "boolean" ? value : fail(path, "expected true or false");

export function oneOf<T extends string>(words: readonly T[]): Reader<T> {
  return (value, path) =>
    words.find((word) => word === value) ?? fail(path, `expected one of ${words.join(", ")}`);
}

export function arrayOf<T>(item: Reader<T>): Reader<T[]> {
  return (value, path) => {
    if (!Array.isArray(value)) return fail(path, "expected a list");
    return (value as unknown[]).map((entry, index) => item(entry, `${path}[${String(index)}]`));
  };
}

/** Every key of `shape` must be present and no other key may be. */
export function object<T extends object>(shape: { [K in keyof T]-?: Reader<T[K]> }): Reader<T> {
  const keys = Object.keys(shape) as (keyof T & string)[];
  return (value, path) => {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return fail(path === "" ? "slice" : path, "expected an object");
    }
    const record = value as Record<string, unknown>;
    for (const key of Object.keys(record)) {
      if (!keys.includes(key as keyof T & string)) fail(child(path, key), "unknown field");
    }
    const out: Partial<T> = {};
    for (const key of keys) {
      if (!Object.hasOwn(record, key)) fail(child(path, key), "missing");
      out[key] = shape[key](record[key], child(path, key));
    }
    return out as T;
  };
}

export const yes: Reader<true> = (value, path) =>
  value === true ? true : fail(path, "expected true");

/** A value that may be null: `null` reads as null, anything else goes to `item`. */
export function orNull<T extends string>(words: readonly T[]): Reader<T | null> {
  const word = oneOf(words);
  return (value, path) => {
    if (value === null) return null;
    if (words.some((w) => w === value)) return word(value, path);
    return fail(path, `expected one of ${words.join(", ")} or null`);
  };
}

/** A reader for an object whose `kind` key names which of `shapes` it must match. */
export function tagged<T extends { kind: string }>(shapes: {
  [K in T["kind"]]: Reader<Extract<T, { kind: K }>>;
}): Reader<T> {
  const kinds = Object.keys(shapes) as T["kind"][];
  return (value, path) => {
    if (typeof value !== "object" || value === null || Array.isArray(value)) {
      return fail(path, "expected an object");
    }
    if (!Object.hasOwn(value, "kind")) return fail(child(path, "kind"), "missing");
    const kind = oneOf(kinds)((value as { kind: unknown }).kind, child(path, "kind"));
    return (shapes[kind] as Reader<T>)(value, path);
  };
}

/** The one word a tagged shape's `kind` key must hold; `tagged` has already matched it. */
export const is =
  <T extends string>(word: T): Reader<T> =>
  (value, path) =>
    value === word ? word : fail(path, `expected ${word}`);

export const at = (path: string, index: number): string => `${path}[${String(index)}]`;

/** The fields every chart's info carries. */
export const chartInfo = { title: text, subtitle: freeText, note: freeText, trace: addressOrNull };

/** Refuses the first item whose `field` an earlier item already has. */
export function distinct<T>(
  list: readonly T[],
  key: (item: T) => string,
  path: string,
  field: string,
  noun: string,
) {
  list.forEach((item, i) => {
    if (list.findIndex((other) => key(other) === key(item)) !== i) {
      fail(`${at(path, i)}.${field}`, `expected a ${field} no other ${noun} has`);
    }
  });
}

/** A trace control as the page draws it: the text that names it, its address and where that text sits. */
export interface TraceName {
  name: string;
  trace: string | null;
  where: string;
}

/**
 * Every drawn trace control on a page is named by its item's delivered text, so no two may share
 * one. An item with no trace draws no control and names nothing. Refuses the second occurrence.
 */
export function distinctTraceNames(items: readonly TraceName[]): void {
  const seen = new Set<string>();
  for (const item of items) {
    if (item.trace === null) continue;
    if (seen.has(item.name)) {
      fail(item.where, "expected a name no other trace control on the page has");
    }
    seen.add(item.name);
  }
}

export function atLeastOne(list: readonly unknown[], path: string, noun: string): void {
  if (list.length === 0) fail(path, `expected at least one ${noun}`);
}
