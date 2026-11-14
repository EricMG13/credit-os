import type { FC } from "react";

export interface IconProps {
  className?: string;
  "data-icon"?: string;
}

/** A function component or a forwardRef component, as opposed to an element or plain content. */
export function isReactComponent(component: unknown): component is FC<IconProps> {
  if (typeof component === "function") return true;
  return (
    typeof component === "object" &&
    component !== null &&
    "$$typeof" in component &&
    String(component.$$typeof) === "Symbol(react.forward_ref)"
  );
}
