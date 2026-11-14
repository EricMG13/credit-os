import type { Marker } from "./series";

interface MarkProps {
  marker: Marker;
  color: string;
  x: number;
  y: number;
  series: string;
}

const R = 4;

/** One marker of the series table, centred on a point. "none" draws nothing. */
export function Mark({ marker, color, x, y, series }: MarkProps) {
  const common = { "data-marker": marker, "data-series": series };
  switch (marker) {
    case "none":
      return null;
    case "circle":
      return <circle {...common} cx={x} cy={y} r={R} fill={color} />;
    case "ring":
      return (
        <circle
          {...common}
          cx={x}
          cy={y}
          r={R}
          fill="var(--color-surface-card)"
          stroke={color}
          strokeWidth={2}
        />
      );
    case "square":
      return <rect {...common} x={x - R} y={y - R} width={2 * R} height={2 * R} fill={color} />;
    case "triangle":
      return (
        <polygon
          {...common}
          points={`${String(x)},${String(y - R - 1)} ${String(x + R + 1)},${String(y + R)} ${String(x - R - 1)},${String(y + R)}`}
          fill={color}
        />
      );
    case "diamond":
      return (
        <polygon
          {...common}
          points={`${String(x)},${String(y - R - 1)} ${String(x + R + 1)},${String(y)} ${String(x)},${String(y + R + 1)} ${String(x - R - 1)},${String(y)}`}
          fill={color}
        />
      );
    case "cross":
      return (
        <path
          {...common}
          d={`M${String(x - R)} ${String(y - R)}L${String(x + R)} ${String(y + R)}M${String(x + R)} ${String(y - R)}L${String(x - R)} ${String(y + R)}`}
          stroke={color}
          strokeWidth={2}
          fill="none"
        />
      );
  }
}
