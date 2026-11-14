/** The issuer header's heading level: App draws the route title as the h1 (ruling R1). Move up one when App changes; the levels below follow. */
export const ISSUER_HEADING = "h2";

const BELOW = { h1: "h2", h2: "h3", h3: "h4" } as const;

/** A page section's heading, one level under the issuer header; its second-level split is one more. */
export const SECTION_HEADING = BELOW[ISSUER_HEADING];
export const SUBSECTION_HEADING = BELOW[SECTION_HEADING];
