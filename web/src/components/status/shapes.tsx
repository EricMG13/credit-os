import type { ReactElement } from "react";

export const SHAPES = [
  "filled circle",
  "half-filled circle",
  "ring",
  "dashed ring",
  "slashed circle",
  "triangle",
  "diamond",
  "square",
  "cross",
  "pause bars",
] as const;

export type Shape = (typeof SHAPES)[number];

const RING = { cx: 5, cy: 5, r: 4.25, fill: "none", stroke: "currentColor", strokeWidth: 1.5 };

const DRAWINGS: Record<Shape, ReactElement> = {
  "filled circle": <circle cx="5" cy="5" r="5" fill="currentColor" />,
  "half-filled circle": (
    <>
      <circle {...RING} />
      <path d="M5 0.75A4.25 4.25 0 0 1 5 9.25Z" fill="currentColor" />
    </>
  ),
  ring: <circle {...RING} />,
  "dashed ring": <circle {...RING} strokeDasharray="1.6 1.4" />,
  "slashed circle": (
    <>
      <circle {...RING} />
      <path d="M1.8 8.2L8.2 1.8" stroke="currentColor" strokeWidth="1.5" />
    </>
  ),
  triangle: <polygon points="5,0.5 9.5,9 0.5,9" fill="currentColor" />,
  diamond: <polygon points="5,0 10,5 5,10 0,5" fill="currentColor" />,
  square: <rect x="1" y="1" width="8" height="8" fill="currentColor" />,
  cross: <path d="M1.5 1.5L8.5 8.5M8.5 1.5L1.5 8.5" stroke="currentColor" strokeWidth="1.8" />,
  "pause bars": (
    <>
      <rect x="1.5" y="1" width="2.5" height="8" fill="currentColor" />
      <rect x="6" y="1" width="2.5" height="8" fill="currentColor" />
    </>
  ),
};

export function StatusShape({ shape }: { shape: Shape }) {
  return (
    <svg
      viewBox="0 0 10 10"
      width="10"
      height="10"
      aria-hidden="true"
      data-shape={shape}
      className="shrink-0"
    >
      {DRAWINGS[shape]}
    </svg>
  );
}
