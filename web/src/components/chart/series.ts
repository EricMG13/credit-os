export type Marker = "circle" | "square" | "triangle" | "diamond" | "ring" | "cross" | "none";

export interface SeriesStyle {
  /** A colour token, never a literal colour. */
  color: string;
  /** The SVG stroke-dasharray of the line; "none" is solid. */
  dash: string;
  marker: Marker;
}

const SOLID = "none";
const DASHED = "6 4";
const DOTTED = "1.5 4";
const DASH_DOT = "8 4 1.5 4";

/** The design system's Chart palette: six slots in order, then Other. */
export const SERIES: readonly SeriesStyle[] = [
  { color: "var(--color-chart-1)", dash: SOLID, marker: "circle" },
  { color: "var(--color-chart-2)", dash: DASHED, marker: "square" },
  { color: "var(--color-chart-3)", dash: SOLID, marker: "triangle" },
  { color: "var(--color-chart-4)", dash: DOTTED, marker: "diamond" },
  { color: "var(--color-chart-5)", dash: SOLID, marker: "ring" },
  { color: "var(--color-chart-6)", dash: DASH_DOT, marker: "cross" },
  { color: "var(--color-chart-other)", dash: SOLID, marker: "none" },
];

const OTHER_SLOT = SERIES.length - 1;

/**
 * The first six names take slots 1 to 6 by position; every later name takes the Other style.
 * It assigns styles only; it never adds series together.
 */
export function assignSeries(names: string[]): Map<string, SeriesStyle> {
  const styles = new Map<string, SeriesStyle>();
  names.forEach((name, i) => {
    const style = SERIES[Math.min(i, OTHER_SLOT)];
    if (style === undefined) throw new Error("the series table is empty");
    styles.set(name, style);
  });
  return styles;
}
