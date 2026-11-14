// Checks on the built #/kit page that only the browser's own engine can answer: the accessible
// names in its accessibility tree (jsdom reads names through a nested role="group" and text with
// visibility:hidden, Chrome does not) and the colour of a keyboard-focused invalid field's ring.
// Drives the browser over its debugging protocol with Node's own fetch and WebSocket.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const designSystem = path.resolve(
  import.meta.dirname,
  "..",
  "..",
  "docs",
  "design",
  "design-system.md",
);
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// The focus colour, as the design system's Colour roles table writes it, as "rgb(r, g, b)".
function focusColour() {
  const row = /^\| `focus` \| `#([0-9A-Fa-f]{6})` /m.exec(readFileSync(designSystem, "utf8"));
  if (!row) throw new Error("design-system.md has no `focus` row in its Colour roles table");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(row[1].slice(i, i + 2), 16));
  return `rgb(${r}, ${g}, ${b})`;
}

async function connect(profile, browserProcess) {
  const portFile = path.join(profile, "DevToolsActivePort");
  for (let i = 0; i < 100 && !existsSync(portFile); i++) await wait(100);
  if (!existsSync(portFile)) throw new Error("the browser did not open its debugging port");
  const port = readFileSync(portFile, "utf8").split("\n")[0];
  const target = await (
    await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })
  ).json();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve);
    socket.addEventListener("error", reject);
    browserProcess.once("exit", () => reject(new Error("the browser exited")));
  });
  const pending = new Map();
  let next = 0;
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    pending.get(message.id)?.(message);
  });
  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++next;
      pending.set(id, (message) =>
        message.error
          ? reject(new Error(`${method}: ${message.error.message}`))
          : resolve(message.result),
      );
      socket.send(JSON.stringify({ id, method, params }));
    });
  return { send, close: () => socket.close() };
}

async function evaluate(send, expression) {
  const { result, exceptionDetails } = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
  });
  if (exceptionDetails) throw new Error(`page script failed: ${exceptionDetails.text}`);
  return result.value;
}

async function press(send, key, code, keyCode) {
  for (const type of ["keyDown", "keyUp"]) {
    await send("Input.dispatchKeyEvent", { type, key, code, windowsVirtualKeyCode: keyCode });
  }
  await wait(300);
}

// Every column header and button the browser exposes has a name.
async function unnamed(send) {
  const { nodes } = await send("Accessibility.getFullAXTree");
  return nodes
    .filter((n) => !n.ignored && ["columnheader", "button"].includes(n.role?.value))
    .filter((n) => (n.name?.value ?? "").trim() === "")
    .map((n) => n.role.value);
}

// A field reached with the Tab key draws the focus colour in its ring (an inset box-shadow).
async function invalidRingColours(send) {
  const fields = `[...document.querySelectorAll("section[aria-labelledby=kit-input] input, section[aria-labelledby=kit-select] button")].filter((e) => e.closest("[data-invalid]") || e.getAttribute("aria-invalid") === "true")`;
  const count = await evaluate(send, `${fields}.length`);
  const colours = [];
  for (let i = 0; i < count; i++) {
    await evaluate(
      send,
      `(() => { const f = ${fields}[${i}]; const all = [...document.querySelectorAll("a[href],button,input,select,textarea,[tabindex]")].filter((e) => e.tabIndex >= 0 && !e.disabled && e.getBoundingClientRect().width > 1); all[all.indexOf(f) - 1].focus(); })()`,
    );
    await press(send, "Tab", "Tab", 9);
    colours.push(
      await evaluate(
        send,
        `(() => { const f = ${fields}[${i}]; if (document.activeElement !== f) return "not reached"; const box = f.tagName === "INPUT" ? f.parentElement : f; return getComputedStyle(box).boxShadow; })()`,
      ),
    );
  }
  return colours;
}

// The link button: its role and name in the browser's accessibility tree, and the ring a
// keyboard-focused link draws (the focus colour, 2px: computed outline).
async function linkButton(send) {
  const { nodes } = await send("Accessibility.getFullAXTree");
  const link = nodes.find(
    (n) => !n.ignored && n.role?.value === "link" && n.name?.value === "Open the library",
  );
  const disabled = nodes.find(
    (n) => !n.ignored && n.role?.value === "link" && n.name?.value === "Library unavailable",
  );
  const target = `[...document.querySelectorAll("section[aria-labelledby=kit-link-button] a")][0]`;
  await evaluate(
    send,
    `(() => { const all = [...document.querySelectorAll("a[href],button,input,select,textarea,[tabindex]")].filter((e) => e.tabIndex >= 0 && !e.disabled && e.getBoundingClientRect().width > 1); all[all.indexOf(${target}) - 1].focus(); })()`,
  );
  await press(send, "Tab", "Tab", 9);
  const ring = await evaluate(
    send,
    `(() => { const f = ${target}; if (document.activeElement !== f) return null; const c = getComputedStyle(f); return { colour: c.outlineColor, width: c.outlineWidth, style: c.outlineStyle }; })()`,
  );
  return { found: Boolean(link), disabledFound: Boolean(disabled), ring };
}

/** Prints PASS or FAIL lines for the kit page opened from file:// and returns true when all pass. */
export async function checkKitInChrome({ browser, folder }) {
  const profile = mkdtempSync(path.join(tmpdir(), "credit-os-cdp-"));
  const child = spawn(
    browser,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--remote-debugging-port=0",
      `--user-data-dir=${profile}`,
      "--window-size=1280,900",
      ...(process.env["CI"] ? ["--no-sandbox"] : []),
      "about:blank",
    ],
    { stdio: "ignore" },
  );
  try {
    const { send, close } = await connect(profile, child);
    await send("Page.enable");
    await send("Page.navigate", {
      url: pathToFileURL(path.join(folder, "index.html")).href + "#/kit",
    });
    await wait(1500);
    const names = await unnamed(send);
    console.log(
      `${names.length === 0 ? "PASS" : "FAIL"} kit page: every column header and button has an accessible name${names.length ? ` (unnamed: ${names.join(", ")})` : ""}`,
    );
    const want = focusColour();
    const rings = await invalidRingColours(send);
    const wrong = rings.filter((shadow) => !shadow.includes(want));
    const ok = rings.length >= 2 && wrong.length === 0;
    console.log(
      `${ok ? "PASS" : "FAIL"} kit page: ${rings.length} keyboard-focused invalid fields draw the focus colour ${want}${ok ? "" : ` (found: ${wrong.join(" | ") || "no invalid fields"})`}`,
    );
    const link = await linkButton(send);
    const linkOk =
      link.found &&
      link.disabledFound &&
      link.ring?.colour === want &&
      link.ring?.width === "2px" &&
      link.ring?.style === "solid";
    console.log(
      `${linkOk ? "PASS" : "FAIL"} kit page: the link button has role link and its label as name (disabled one too) and a keyboard-focused one draws a 2px ${want} outline${linkOk ? "" : ` (found: ${JSON.stringify(link)})`}`,
    );
    close();
    return names.length === 0 && ok && linkOk;
  } finally {
    child.kill("SIGKILL");
    rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}
