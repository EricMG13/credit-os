import { render, screen } from "@testing-library/react";
import { PairTile, type PairTileEntry } from "./PairTile";

// Strings are copied from the mock (Model 4 Portfolio fit, "Agency ratings").
const TILES: [PairTileEntry, PairTileEntry] = [
  { label: "Moody's, corporate family", value: "B1", caption: "Stable outlook" },
  { label: "S&P, issuer credit", value: "B+", caption: "Stable outlook" },
];

describe("PairTile", () => {
  it("shows both agencies' labels, ratings and outlooks, with no toggle", () => {
    render(<PairTile tiles={TILES} />);
    const cards = screen.getAllByRole("article");
    expect(cards.map((c) => c.textContent)).toEqual([
      "Moody's, corporate familyB1",
      "S&P, issuer creditB+",
    ]);
    expect(screen.getAllByText("Stable outlook")).toHaveLength(2);
    expect(screen.queryByRole("radio")).toBeNull();
  });

  it("draws n.a. for a missing rating and no caption when none is given", () => {
    render(<PairTile tiles={[{ label: "Moody's, corporate family", value: null }, TILES[1]]} />);
    expect(screen.getAllByRole("article")[0]).toHaveTextContent("n.a.");
    expect(screen.getAllByText("Stable outlook")).toHaveLength(1);
  });

  it("throws when the two tiles share a label", () => {
    expect(() => render(<PairTile tiles={[TILES[0], TILES[0]]} />)).toThrow(/distinct/);
  });
});
