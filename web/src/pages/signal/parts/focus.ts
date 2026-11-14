// Focus behaviour the Signal dialogs and panels share.
import { useEffect, useRef } from "react";

/** Runs once when a dialog's or panel's content goes (after any exit animation), so focus never falls to the page. */
export function useOnGone(then: () => void) {
  const latest = useRef(then);
  useEffect(() => {
    latest.current = then;
  });
  useEffect(
    () => () => {
      latest.current();
    },
    [],
  );
}

/**
 * Focus goes to the target at once and again two frames later if it has fallen to the page: the
 * dialog library restores focus a frame late, and in a browser that restore can leave focus on the body.
 */
export function focusAgainIfLost(target: () => HTMLElement | null | undefined) {
  target()?.focus();
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (document.activeElement === null || document.activeElement === document.body) {
        target()?.focus();
      }
    });
  });
}
