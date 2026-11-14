/** Every link in the library group is a hash link, built here so the address scheme lives in one place. */
const seg = encodeURIComponent;

/** The run start page, the target of "Start a run" and "New run". */
export const RUN_START = "#/run";

const historyHref = (issuer: string): string => `#/library/${seg(issuer)}/history`;

const overviewHref = (issuer: string, run: string): string =>
  `#/library/${seg(issuer)}/${seg(run)}/overview`;

/** Where an issuer's card leads: the latest finished run's Overview, or the history when there is none. */
export const cardHref = (issuer: string, run: string | null): string =>
  run === null ? historyHref(issuer) : overviewHref(issuer, run);
