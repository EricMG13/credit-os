import { createContext, useContext } from "react";
import type { LibraryData } from "../data";

/** The loaded library, provided by App to the page of a matched route. */
export const SourceContext = createContext<LibraryData | null>(null);

/** A page reads its group's member with `readSlice(useSource().<group>)`. */
export function useSource(): LibraryData {
  const source = useContext(SourceContext);
  if (source === null) throw new Error("useSource was called outside a loaded library");
  return source;
}
