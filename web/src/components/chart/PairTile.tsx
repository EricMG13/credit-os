import { MetricCard } from "@/components/metric/MetricCard";

export interface PairTileEntry {
  label: string;
  /** The display string; null when missing. */
  value: string | null;
  /** The line under the figure, as delivered ("Stable outlook"); omitted when there is none. */
  caption?: string;
}

/** Two ratings side by side, each a kit metric card. It is not a chart and has no toggle. */
export function PairTile({ tiles }: { tiles: [PairTileEntry, PairTileEntry] }) {
  if (tiles[0].label === tiles[1].label) {
    throw new Error(`the two tiles must have distinct labels: "${tiles[0].label}" repeats`);
  }
  return (
    <div className="grid grid-cols-1 gap-4 rounded-lg border border-border-hairline bg-surface-subtle p-4 sm:grid-cols-2">
      {tiles.map((t) => (
        <div key={t.label} className="flex min-w-0 flex-col gap-2">
          <MetricCard label={t.label} value={t.value} />
          {t.caption === undefined ? null : (
            <p className="px-1 text-small font-medium text-text-secondary">{t.caption}</p>
          )}
        </div>
      ))}
    </div>
  );
}
