import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

function current(): string {
  return window.location.hash.slice(1);
}

/** The part of the address after "#", empty when there is none. No router package (decision 0001). */
export function useHashRoute(): string {
  return useSyncExternalStore(subscribe, current);
}
