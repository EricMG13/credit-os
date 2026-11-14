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
const QUOTED = { '"': /"((?:[^"\\\n]|\\.)*)"/y, "'": /'((?:[^'\\\n]|\\.)*)'/y };

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

// Reads a template literal body from `i` (just after the opening backtick). Each static run is
// pushed with "${}" standing for an interpolation, so a token cut by one is never taken for a
// class; the interpolation's own code is scanned like any other. Returns the index after it.
function readTemplate(text, i, out) {
  let run = "";
  while (i < text.length) {
    const ch = text[i];
    if (ch === "\\") {
      run += text.slice(i, i + 2);
      i += 2;
    } else if (ch === "`") {
      out.push(run);
      return i + 1;
    } else if (ch === "$" && text[i + 1] === "{") {
      run += "${}";
      i = scanCode(text, i + 2, true, out);
    } else {
      run += ch;
      i++;
    }
  }
  out.push(run);
  return i;
}

// Pushes the content of every string and template literal found in code from `start`, skipping
// comments. In an interpolation it stops after the brace that closes it and returns that index.
function scanCode(text, start, inInterpolation, out) {
  let depth = 0;
  let i = start;
  while (i < text.length) {
    const ch = text[i];
    const pair = text.slice(i, i + 2);
    if (pair === "//") {
      const end = text.indexOf("\n", i);
      i = end < 0 ? text.length : end;
    } else if (pair === "/*") {
      const end = text.indexOf("*/", i + 2);
      i = end < 0 ? text.length : end + 2;
    } else if (ch === "`") {
      i = readTemplate(text, i + 1, out);
    } else if (ch === '"' || ch === "'") {
      const pattern = QUOTED[ch];
      pattern.lastIndex = i;
      const m = pattern.exec(text);
      // A quote with no partner on its line (an apostrophe in JSX text) is not a string.
      if (m) out.push(m[1]);
      i = m ? i + m[0].length : i + 1;
    } else if (inInterpolation && ch === "{") {
      depth++;
      i++;
    } else if (inInterpolation && ch === "}") {
      if (depth === 0) return i + 1;
      depth--;
      i++;
    } else {
      i++;
    }
  }
  return i;
}

// Tokens of the string literals in a source text that name a colour, shadow, radius or size class.
export function utilityTokens(text) {
  const strings = [];
  scanCode(text, 0, false, strings);
  const found = [];
  for (const content of strings) {
    for (const token of content.split(/\s+/)) {
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
