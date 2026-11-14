import { render } from "@testing-library/react";
import { createElement } from "react";
import { ColumnsChart } from "./ColumnsChart";

// Values, labels and table strings are copied from the mock's script block (Model 3 Model).
const MAT_GROUPS = ["2026", "2027", "2028", "2029", "2030", "2031 on"];
const MAT_SERIES = [
  {
    name: "Term loans",
    values: [null, 0, 3600, 0, 4500, 3200],
    labels: [null, "0", "3,600", "0", "4,500", "3,200"],
  },
  {
    name: "Secured notes",
    values: [0, 0, 2100, 2750, 1450, 4150],
    labels: ["0", "0", "2,100", "2,750", "1,450", "4,150"],
  },
  {
    name: "Subordinated notes",
    values: [0, 550, 0, 2650, 0, 4100],
    labels: ["0", "550", "0", "2,650", "0", "4,100"],
  },
];
const MAT_TICKS = [
  { value: 0, label: "0" },
  { value: 1250, label: "1,250" },
  { value: 2500, label: "2,500" },
  { value: 3750, label: "3,750" },
  { value: 5000, label: "5,000" },
];
const MAT_TABLE = {
  head: ["Year", "Term loans", "Secured notes", "Subordinated notes"],
  rows: [
    { label: "2026", cells: [null, "0", "0"] },
    { label: "2027", cells: ["0", "0", "550"] },
    { label: "2028", cells: ["3,600", "2,100", "0"] },
    { label: "2029", cells: ["0", "2,750", "2,650"] },
    { label: "2030", cells: ["4,500", "1,450", "0"] },
    { label: "2031 on", cells: ["3,200", "4,150", "4,100"] },
  ],
};

const REC_GROUPS = [
  "Term loans and secured notes",
  "Senior subordinated notes",
  "Receivables facility",
];
const REC_SERIES = [
  { name: "Base case", values: [100, 62, 100], labels: ["100%", "62%", "100%"] },
  { name: "Downside case", values: [100, 31, null], labels: ["100%", "31%", null] },
];
const REC_TABLE = {
  head: ["Class", "Base case", "Downside case"],
  rows: [
    { label: "Term loans and secured notes", cells: ["100%", "100%"] },
    { label: "Senior subordinated notes", cells: ["62%", "31%"] },
    { label: "Receivables facility", cells: ["100%", null] },
  ],
};
const REC_TICKS = [
  { value: 0, label: "0" },
  { value: 50, label: "50%" },
  { value: 100, label: "100%" },
];

export function renderMat() {
  return render(
    createElement(ColumnsChart, {
      title: "Maturities by year",
      subtitle: "Calendar years, USD millions",
      groups: MAT_GROUPS,
      series: MAT_SERIES,
      yTicks: MAT_TICKS,
      table: MAT_TABLE,
    }),
  );
}

export function renderRec() {
  return render(
    createElement(ColumnsChart, {
      title: "Recovery by class and case",
      groups: REC_GROUPS,
      series: REC_SERIES,
      yTicks: REC_TICKS,
      table: REC_TABLE,
    }),
  );
}

export function bars(container: HTMLElement) {
  return [...container.querySelectorAll(".recharts-wrapper [data-bar]")];
}
export function barOf(container: HTMLElement, series: string, group: string): Element | undefined {
  return bars(container).find(
    (b) => b.getAttribute("data-series") === series && b.getAttribute("data-group") === group,
  );
}
