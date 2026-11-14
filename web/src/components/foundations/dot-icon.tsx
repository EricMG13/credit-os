import type { HTMLAttributes } from "react";

export const Dot = (props: HTMLAttributes<HTMLOrSVGElement>) => {
  return (
    <svg width={8} height={8} viewBox="0 0 8 8" fill="none" {...props}>
      <circle cx={4} cy={4} r={2.5} fill="currentColor" stroke="currentColor" />
    </svg>
  );
};
