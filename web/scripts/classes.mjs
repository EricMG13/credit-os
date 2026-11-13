// Class coverage: every Tailwind colour, shadow, radius or size class named in the source must
// have a rule in the built stylesheet. The default palette is off, so a class with no theme token
// silently draws nothing; this check is the guard.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const FAMILIES = [
  "bg",
  "text",
  "border",
  "ring",
  "outline",
  "fill",
  "stroke",
  "divide",
  "shadow",
  "rounded",
  "from",
  "to",
  "via",
];
const UTILITY = new RegExp(`^[!-]*(?:${FAMILIES.join("|")})-\\S+$`);
const STRING = /"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`/g;

// The text after the last ":" that is not inside brackets or parentheses, which is the utility
// once its variants are removed.
function afterVariants(token) {
  let depth = 0;
  let cut = -1;
  for (let i = 0; i < token.length; i++) {
    const ch = token[i];
    if (ch === "[" || ch === "(") depth++;
    else if (ch === "]" || ch === ")") depth--;
    else if (ch === ":" && depth === 0) cut = i;
  }
  return token.slice(cut + 1);
}

// Tokens of the string literals in a source text that name a colour, shadow, radius or size class.
export function utilityTokens(text) {
  const found = [];
  for (const m of text.matchAll(STRING)) {
    for (const token of (m[1] ?? m[2] ?? m[3] ?? "").split(/\s+/)) {
      if (token === "" || /[${}]/.test(token)) continue;
      if (UTILITY.test(afterVariants(token))) found.push(token);
    }
  }
  return found;
}

// Every class name that appears as a selector in a stylesheet, with CSS escapes read back.
export function builtClasses(css) {
  const names = new Set();
  for (const m of css.matchAll(/\.((?:\\[0-9a-fA-F]{1,6}\s?|\\.|[\w-])+)/g)) {
    names.add(
      m[1].replace(/\\([0-9a-fA-F]{1,6})\s?|\\(.)/g, (_, hex, ch) =>
        hex ? String.fromCodePoint(Number.parseInt(hex, 16)) : ch,
      ),
    );
  }
  return names;
}

function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(full);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [full] : [];
  });
}

// One message per class with no rule; an empty list means every class is covered. `allowed` lists
// strings that are not classes, each with its reason in the caller.
export function classProblems(srcDir, css, allowed) {
  const built = builtClasses(css);
  const problems = new Set();
  for (const file of sourceFiles(srcDir)) {
    for (const token of utilityTokens(readFileSync(file, "utf8"))) {
      if (!built.has(token) && !allowed.includes(token)) {
        problems.add(
          `${path.relative(srcDir, file)}: ${token} has no rule in the built stylesheet`,
        );
      }
    }
  }
  return [...problems].sort();
}
