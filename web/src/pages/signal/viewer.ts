// The viewer's name and initials as the frame holds them (a typed name replaces the slice's), for a
// page inside the frame that writes under that name. Null name: none is set yet.
import { createContext, useContext } from "react";

export type SignalViewerName = { name: string | null; initials: string | null };

export const SignalViewerContext = createContext<SignalViewerName | null>(null);

export function useSignalViewer(): SignalViewerName {
  const viewer = useContext(SignalViewerContext);
  if (viewer === null) throw new Error("a Signal page was drawn outside the Signal frame");
  return viewer;
}
