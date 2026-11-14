import {
  addressOrNull,
  arrayOf,
  at,
  atLeastOne,
  chartInfo as info,
  child,
  distinct,
  fail,
  num,
  numOrNull,
  object,
  pairOf,
  text,
  textOrNull,
  type Reader,
} from "./reader-kit";
import type {
  Limits,
  LimitsColumn,
  PortfolioFitPage,
  RatingTile,
  Ratings,
  RelativeValue,
} from "./types";

const pairCells = pairOf(textOrNull);

const limitColumn = object<LimitsColumn>({
  label: text,
  exposure: numOrNull,
  limit: numOrNull,
  scaleMax: num,
  exposureText: textOrNull,
  limitText: textOrNull,
  cells: pairCells,
});
const limits = object<Limits>({ ...info, head: arrayOf(text), columns: arrayOf(limitColumn) });
const tile = object<RatingTile>({ label: text, value: textOrNull, caption: textOrNull });
const ratings = object<Ratings>({
  title: text,
  trace: addressOrNull,
  tiles: pairOf(tile),
});
const relativeValue = object<RelativeValue>({ title: text, part: text, reason: text });

export const portfolioFit: Reader<PortfolioFitPage> = object<PortfolioFitPage>({
  limits,
  ratings,
  relativeValue,
});

/** A value and its text are `null` together; the words say which pair. */
function checkPair(
  value: number | null,
  shown: string | null,
  where: string,
  noun: string,
  range: string | null,
): void {
  if (value === null) {
    if (shown !== null) fail(where, `expected null beside a missing ${noun}`);
    return;
  }
  if (shown === null) fail(where, `expected a text beside a present ${noun}`);
  if (range !== null) fail(where.replace(/Text$/, ""), range);
}

function checkLimits(l: Limits, path: string): void {
  if (l.head.length !== 3) {
    fail(`${path}.head`, "expected 3 headings: the label, the exposure and the limit");
  }
  atLeastOne(l.columns, `${path}.columns`, "column");
  distinct(l.columns, (c) => c.label, `${path}.columns`, "label", "column");
  l.columns.forEach((c, i) => {
    const where = at(`${path}.columns`, i);
    if (!(c.scaleMax > 0)) fail(`${where}.scaleMax`, "expected a number above zero");
    const range = `expected a position from 0 to the scale (${String(c.scaleMax)})`;
    for (const kind of ["exposure", "limit"] as const) {
      const value = c[kind];
      const out = value !== null && !(value >= 0 && value <= c.scaleMax);
      checkPair(value, c[`${kind}Text`], `${where}.${kind}Text`, kind, out ? range : null);
    }
    if (c.cells[0] !== c.exposureText) {
      fail(`${where}.cells[0]`, "expected the column's exposure text");
    }
    if (c.limitText === null) {
      if (c.cells[1] !== null) fail(`${where}.cells[1]`, "expected null beside a missing limit");
    } else if (c.cells[1] === null || c.limitText !== `limit ${c.cells[1]}`) {
      fail(`${where}.cells[1]`, "expected the column's limit text without its word");
    }
  });
}

/** Every rule the page and its charts enforce, so a slice that reads ok never throws there. */
export function checkPortfolioFit(page: PortfolioFitPage, path: string): void {
  checkLimits(page.limits, child(path, "limits"));
  const [first, second] = page.ratings.tiles;
  if (first.label === second.label) {
    fail(
      `${child(path, "ratings.tiles")}[1].label`,
      "expected a label the other tile does not have",
    );
  }
}
