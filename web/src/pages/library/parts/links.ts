/** Every link in the library group is a hash link, built here so the address scheme lives in one place. */
const seg = encodeURIComponent;

/** The run start page, the target of "Start a run" and "New run". */
export const RUN_START = "#/run";

/** The library home, the target of every "Library" and "Back to the library" link. */
export const LIBRARY_HOME = "#/library/home";

/**
 * Every text link in the library pages: the design focus ring in place of the browser's outline.
 * Colour and underline are the caller's.
 */
export const TEXT_LINK =
  "rounded-ds-xs outline-hidden focus-visible:ring-2 focus-visible:ring-brand";

const historyHref = (issuer: string): string => `#/library/${seg(issuer)}/history`;

export const overviewHref = (issuer: string, run: string): string =>
  `#/library/${seg(issuer)}/${seg(run)}/overview`;

/** Where an issuer's card leads: the latest finished run's Overview, or the history when there is none. */
export const cardHref = (issuer: string, run: string | null): string =>
  run === null ? historyHref(issuer) : overviewHref(issuer, run);

/** The Changes page of a run: the target of an entry's "What changed since …" link. */
export const changesHref = (issuer: string, run: string): string =>
  `#/library/${seg(issuer)}/${seg(run)}/changes`;
