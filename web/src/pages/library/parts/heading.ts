/** The issuer header's heading level: every library route is full bleed and the issuer name is the page's h1. The levels below follow. */
export const ISSUER_HEADING = "h1";

const BELOW = { h1: "h2", h2: "h3", h3: "h4" } as const;

/** A page section's heading, one level under the issuer header; its second-level split is one more. */
export const SECTION_HEADING = BELOW[ISSUER_HEADING];
export const SUBSECTION_HEADING = BELOW[SECTION_HEADING];
