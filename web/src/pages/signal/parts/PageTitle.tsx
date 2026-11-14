// A Signal page's title: the page's one h1 (the shell draws none for a full-bleed page), at the
// size the mock gives its view heading (`.vh h2`: the design system's h2 step). With `titleRef` it
// takes focus by script (a page moves focus here when what it was moving to is gone).
import type { ReactNode, Ref } from "react";

export function PageTitle({
  children,
  titleRef,
}: {
  children: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
}) {
  return (
    <h1
      ref={titleRef}
      tabIndex={titleRef === undefined ? undefined : -1}
      className="text-h2 text-text-primary outline-focus-ring focus-visible:outline-2"
    >
      {children}
    </h1>
  );
}
