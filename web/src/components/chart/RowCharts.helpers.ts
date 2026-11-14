import { fireEvent, render, screen, within } from "@testing-library/react";

export function rowOf(label: string) {
  const row = screen.getByText(label).closest("[data-row]");
  if (!(row instanceof HTMLElement)) throw new Error(`no row ${label}`);
  return row;
}
export const num = (el: Element | null, attr: string) => Number(el?.getAttribute(attr));
export function throwsOn(ui: React.ReactElement, pattern: RegExp) {
  const quiet = vi.spyOn(console, "error").mockImplementation(() => undefined);
  expect(() => render(ui)).toThrow(pattern);
  quiet.mockRestore();
}
export function tableCells(label: string) {
  fireEvent.click(screen.getByRole("radio", { name: "Table" }));
  return within(screen.getByRole("row", { name: new RegExp(label) }))
    .getAllByRole("cell")
    .map((c) => c.textContent.replace("not available", ""));
}
export function legendTexts() {
  return within(screen.getByRole("list", { name: "Legend" }))
    .getAllByRole("listitem")
    .map((li) => li.textContent);
}
export function noFocusStopInChart(container: HTMLElement) {
  expect(
    container.querySelectorAll(
      "[data-row] :is([tabindex], a, button, input), [aria-label=Legend] [tabindex]",
    ),
  ).toHaveLength(0);
  expect(container.querySelector(".recharts-wrapper")).toBeNull();
}
