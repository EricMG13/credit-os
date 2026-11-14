import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./slice";

type Node = Record<string | number, unknown>;
const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../fixtures/run.json"), "utf8"),
) as { slice: unknown };
// A copy of the fixture slice with one record's value at `at` replaced (undefined removes it).
function editIn(
  key: "drafts" | "runs",
  id: string,
  at: (string | number)[],
  value: unknown,
): unknown {
  const copy = structuredClone(fixture.slice) as Record<"drafts" | "runs", Node[]>;
  let node: Node = copy[key].find((d) => d.id === id) ?? {};
  for (const k of at.slice(0, -1)) node = node[k] as Node;
  const last = at[at.length - 1] ?? "";
  if (value === undefined) Reflect.deleteProperty(node, last);
  else node[last] = value;
  return copy;
}
const edit = (id: string, at: (string | number)[], value: unknown) =>
  editIn("drafts", id, at, value);
const editRun = (id: string, at: (string | number)[], value: unknown) =>
  editIn("runs", id, at, value);
const reason = (source: unknown): string => {
  const r = readSlice(source);
  return r.kind === "invalid" ? r.reason : `not invalid: ${r.kind}`;
};

describe("committed fixture", () => {
  it("reads as ok with its seven drafts in order", () => {
    const r = readSlice(fixture.slice);
    expect(r.kind).toBe("ok");
    if (r.kind !== "ok") return;
    expect(r.data.drafts.map((d) => d.id)).toEqual([
      "no-documents",
      "documents",
      "purpose",
      "confirm",
      "context",
      "start",
      "started",
    ]);
  });

  it("keeps the exact strings of each step kind", () => {
    const r = readSlice(fixture.slice);
    if (r.kind !== "ok") throw new Error("fixture invalid");
    const by = (id: string) => r.data.drafts.find((d) => d.id === id);
    const docs = by("documents");
    if (docs?.step !== "documents") throw new Error("step");
    expect(docs.files[2]).toEqual({
      name: "Credit agreement, latest amendment.pdf",
      kind: "PDF",
      size: "1.3 MB",
      state: "Uploading",
      progress: { label: "62%", value: 62, max: 100 },
      reason: null,
    });
    expect(docs.files).toHaveLength(6);
    expect(docs.files[5]).toEqual({
      name: "Synthetic annual report with supplementary schedules and notes for the year AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA final.pdf",
      kind: "PDF",
      size: "6.2 MB",
      state: "Read in full",
      progress: { label: "100%", value: 100, max: 100 },
      reason: null,
    });
    expect(docs.nextBlocked).toBe("Replace or remove the unreadable file to continue.");
    const purpose = by("purpose");
    if (purpose?.step !== "purpose") throw new Error("step");
    expect(purpose.chosen).toBe("full-review");
    expect(purpose.purposes[1]?.title).toBe("Earnings update");
    expect(purpose.purposes[1]?.modules).toBe("5 modules");
    expect(purpose.purposes).toHaveLength(4);
    expect(purpose.purposes[3]).toEqual({
      id: "long-label",
      title: "Long label review",
      description: "A synthetic purpose whose module label is long, to show that the label wraps.",
      modules: "14 modules, from documents and business profile to forecast, recovery and rating",
    });
    const confirm = by("confirm");
    if (confirm?.step !== "confirm") throw new Error("step");
    expect(confirm.nextLabel).toBe("Approve summary");
    expect(confirm.groups[0]?.rows[4]).toEqual({ label: "Guarantor group", value: null });
    expect(confirm.readiness.notMet).toEqual({ count: "1", items: ["Summary approved"] });
    const context = by("context");
    if (context?.step !== "context") throw new Error("step");
    expect(context.note).toBe("");
    const start = by("start");
    if (start?.step !== "start") throw new Error("step");
    expect(start.nextLabel).toBe("Submit, spend up to USD 20.00");
    expect(start.paid.amount).toBe("USD 20.00");
    expect(start.confirm.action).toBe("Start run, up to USD 20.00");
    expect(start.confirm.started).toBe("started");
    expect(start.readiness.line).toBe("Everything the run needs is in place.");
    const started = by("started");
    if (started?.step !== "started") throw new Error("step");
    expect(started.title).toBe("Run started");
    expect(started.activity).toBe("running");
    expect(started.next).toBeNull();
    expect(started.cap).toEqual({ label: "USD 0.00 of USD 20.00", value: 0, max: 20 });
  });

  it("keeps a null value as null and a zero bar as 0", () => {
    const r = readSlice(fixture.slice);
    if (r.kind !== "ok") throw new Error("fixture invalid");
    const confirm = r.data.drafts.find((d) => d.id === "confirm");
    if (confirm?.step !== "confirm") throw new Error("step");
    expect(confirm.groups[0]?.rows[4]?.value).toBeNull();
    expect(confirm.readiness.cap.value).toBe(0);
  });
});

describe("top level", () => {
  it("is absent for undefined", () => {
    expect(readSlice(undefined)).toEqual({ kind: "absent" });
  });
  it.each([null, [], "text"])("is invalid for %j", (v) => {
    expect(reason(v)).toBe("run: expected an object");
  });
});

describe("rejects", () => {
  it("a non-string where a string is required", () => {
    expect(reason(edit("documents", ["files", 4, "name"], 5))).toBe(
      "run.drafts[1].files[4].name: expected a string",
    );
  });
  it("an unknown step", () => {
    expect(reason(edit("purpose", ["step"], "pay"))).toBe(
      "run.drafts[2].step: expected one of documents, purpose, confirm, context, start, started",
    );
  });
  it("an unknown file state", () => {
    expect(reason(edit("documents", ["files", 4, "state"], "Lost"))).toBe(
      "run.drafts[1].files[4].state: expected one of Uploading, Read in full, Read in part, Unreadable",
    );
  });
  it("a bar whose max is not above 0", () => {
    expect(reason(edit("documents", ["files", 2, "progress", "max"], 0))).toBe(
      "run.drafts[1].files[2].progress.max: expected a number above 0",
    );
  });
  it.each([-1, 101, null, "62"])("a bar whose value is %j", (value) => {
    expect(reason(edit("documents", ["files", 2, "progress", "value"], value))).toBe(
      "run.drafts[1].files[2].progress.value: expected a number from 0 to max",
    );
  });
  it("a readiness cap that is not a bar", () => {
    expect(reason(edit("context", ["readiness", "cap", "max"], -20))).toBe(
      "run.drafts[4].readiness.cap.max: expected a number above 0",
    );
  });
  it("a duplicate draft id", () => {
    expect(reason(edit("context", ["id"], "purpose"))).toBe(
      "run.drafts[4].id: expected an id no other draft uses",
    );
  });
  it("a previous that names no draft", () => {
    expect(reason(edit("purpose", ["previous"], "nowhere"))).toBe(
      "run.drafts[2].previous: expected null or the id of a draft in this slice",
    );
  });
  it("a next that names no draft", () => {
    expect(reason(edit("purpose", ["next"], "nowhere"))).toBe(
      "run.drafts[2].next: expected null or the id of a draft in this slice",
    );
  });
  it("a confirm.started that names no draft", () => {
    expect(reason(edit("start", ["confirm", "started"], "nowhere"))).toBe(
      "run.drafts[5].confirm.started: expected the id of a draft in this slice",
    );
  });
  it("a confirm.started that is null", () => {
    expect(reason(edit("start", ["confirm", "started"], null))).toBe(
      "run.drafts[5].confirm.started: expected a string",
    );
  });
  it("a missing nullable string, naming both halves", () => {
    expect(reason(edit("documents", ["files", 4, "reason"], undefined))).toBe(
      "run.drafts[1].files[4].reason: expected a string or null",
    );
    expect(reason(edit("documents", ["previous"], 3))).toBe(
      "run.drafts[1].previous: expected a string or null",
    );
  });
  it("a missing or wrong-typed nullable bar, naming both halves", () => {
    expect(reason(edit("documents", ["files", 2, "progress"], undefined))).toBe(
      "run.drafts[1].files[2].progress: expected an object or null",
    );
    expect(reason(edit("documents", ["files", 2, "progress"], "62%"))).toBe(
      "run.drafts[1].files[2].progress: expected an object or null",
    );
  });
  it("two purposes with the same id in one draft", () => {
    const purposes = [
      { id: "same", title: "A", description: "a", modules: "1 module" },
      { id: "same", title: "B", description: "b", modules: "2 modules" },
    ];
    expect(reason(edit("purpose", ["purposes"], purposes))).toBe(
      "run.drafts[2].purposes[1].id: expected an id no other purpose uses",
    );
  });
  it("two confirm groups with the same name in one draft", () => {
    const groups = [
      { name: "Issuer", rows: [] },
      { name: "Issuer", rows: [] },
    ];
    expect(reason(edit("confirm", ["groups"], groups))).toBe(
      "run.drafts[3].groups[1].name: expected a name no other group uses",
    );
  });
  it("a chosen purpose that is not one of its purposes", () => {
    expect(reason(edit("purpose", ["chosen"], "nowhere"))).toBe(
      "run.drafts[2].chosen: expected null or the id of one of its purposes",
    );
  });
  it("a started draft with a next", () => {
    expect(reason(edit("started", ["next"], "start"))).toBe(
      "run.drafts[6].next: expected null on a started draft",
    );
  });
  it("a step other than started with no next and no reason", () => {
    expect(reason(edit("purpose", ["next"], null))).toBe(
      "run.drafts[2].nextBlocked: expected a reason when next is null",
    );
  });
  it("a step with no next but a reason is read", () => {
    const source = edit("purpose", ["next"], null);
    const copy = source as { drafts: Node[] };
    (copy.drafts[2] as Node).nextBlocked = "Not yet.";
    expect(readSlice(source).kind).toBe("ok");
  });
  it("a missing list", () => {
    expect(reason(edit("documents", ["files"], undefined))).toBe(
      "run.drafts[1].files: expected a list",
    );
  });
});

describe("unknown keys", () => {
  it("are ignored and not returned", () => {
    const r = readSlice(edit("context", ["extra"], "x"));
    expect(r.kind).toBe("ok");
    if (r.kind === "ok") expect(Object.keys(r.data.drafts[4] ?? {})).not.toContain("extra");
  });
});

type Slice = Extract<ReturnType<typeof readSlice>, { kind: "ok" }>["data"];
type Rec = Extract<Slice["runs"][number], { kind: "run" }>;
function read(): Slice {
  const r = readSlice(fixture.slice);
  if (r.kind !== "ok") throw new Error("fixture invalid");
  return r.data;
}
function run(id: string): Rec {
  const found = read().runs.find((x) => x.id === id);
  if (found?.kind !== "run") throw new Error(`no run ${id}`);
  return found;
}
function steps(id: string) {
  const m = run(id).modules;
  if (m.kind !== "steps") throw new Error("not steps");
  return m.steps;
}
const SPEND = (label: string, value: number) => ({ label, value, max: 20 });

describe("committed fixture, run activity", () => {
  it("holds eleven records in order and a current run", () => {
    const data = read();
    expect(data.runs.map((x) => x.id)).toEqual([
      "running",
      "queued",
      "starting",
      "finished",
      "failed",
      "capped",
      "rejected",
      "interrupted",
      "many-modules",
      "none",
      "unreadable",
    ]);
    expect(data.current).toBe("running");
  });

  it("running and queued", () => {
    const r = run("running");
    expect(r).toMatchObject({
      issuer: "TransDigm Group",
      state: "Running",
      labels: ["Full credit review", "As of Q3 FY2026"],
      line: null,
      alert: null,
      open: null,
      spend: { value: "USD 7.40", bar: SPEND("USD 7.40 of USD 20.00", 7.4) },
      finished: { value: "5 of 13", bar: { label: "5 of 13 modules", value: 5, max: 13 } },
      elapsed: { value: "16 min 12 s", note: "Started today at 14:38" },
    });
    expect(steps("running")).toHaveLength(13);
    expect(steps("running")[4]).toEqual({
      kind: "module",
      name: "Liquidity",
      state: "Finished",
      detail: "Finished in 3 min 20 s, USD 1.62",
    });
    expect(steps("running")[5]).toEqual({
      kind: "module",
      name: "Covenants",
      state: "Running",
      detail: "Started at 14:54",
    });
    expect(steps("running")[6]).toEqual({
      kind: "module",
      name: "Peer comparison",
      state: "Queued",
      detail: null,
    });
    expect(r.feed).toHaveLength(7);
    expect(r.feed[0]).toEqual({
      who: "Covenants",
      time: "14:54",
      text: "Started.",
      state: "Running",
    });
    expect(r.feed[6]).toEqual({
      who: "Run",
      time: "14:38",
      text: "Started. 13 modules queued, cap USD 20.00.",
      state: "Queued",
    });
    const q = run("queued");
    expect(q.state).toBe("Queued");
    expect(q.line).toBe("Waiting for the model service. Nothing has been spent.");
    expect(q.elapsed).toEqual({ value: null, note: "Not started yet" });
    expect(q.spend.bar?.value).toBe(0);
    expect(steps("queued").every((m) => m.kind === "module" && m.state === "Queued")).toBe(true);
    expect(q.feed).toEqual([
      {
        who: "Run",
        time: "14:37",
        text: "Submitted and queued. 13 modules, cap USD 20.00.",
        state: "Queued",
      },
    ]);
  });

  it("starting, with no finished figure", () => {
    const r = run("starting");
    expect(r.modules).toEqual({
      kind: "starting",
      label: "Starting the run. No module has reported yet.",
    });
    expect(r.finished).toEqual({ value: null, note: "No module has reported yet", bar: null });
    expect(r.elapsed).toEqual({ value: "0 min 08 s", note: "Started today at 14:38" });
    expect(r.feed).toHaveLength(1);
  });

  it("finished", () => {
    const r = run("finished");
    expect(r.open).toEqual({ label: "Open the library", href: "#/" });
    expect(r.spend.value).toBe("USD 16.65");
    expect(r.finished.value).toBe("12 of 13");
    expect(steps("finished")[9]).toEqual({
      kind: "module",
      name: "Recovery",
      state: "Not assessable",
      detail:
        "The documents supplied do not state the security package, so recovery could not be assessed.",
    });
    expect(r.feed[3]).toEqual({
      who: "Recovery",
      time: "15:09",
      text: "Not assessable: the security package is not stated in the documents.",
      state: "Not assessable",
    });
    expect(r.feed).toHaveLength(6);
  });

  it("failed, capped, rejected and interrupted", () => {
    const failed = run("failed");
    expect(failed.alert).toEqual({
      title: "The run failed",
      text: "Financial analysis stopped after three attempts because the model service returned no usable answer. Two modules finished and are kept. Starting again goes through Start and asks before it spends.",
      action: { label: "Review and start again", href: "#/run/start/start" },
      alt: { label: "Open what finished", href: "#/" },
    });
    expect(steps("failed")[2]).toMatchObject({ state: "Not assessable" });
    expect(steps("failed")[3]).toMatchObject({ state: "Not run", detail: "Did not run." });
    expect(failed.feed[0]).toEqual({
      who: "Run",
      time: "14:48",
      text: "Failed. USD 3.10 spent.",
      state: "Failed",
    });
    const capped = run("capped");
    expect(capped.spend.bar).toEqual(SPEND("USD 20.00 of USD 20.00", 20));
    expect(capped.alert?.action).toEqual({ label: "Open what finished", href: "#/" });
    expect(capped.alert?.alt).toEqual({
      label: "Start a new run",
      href: "#/run/start/no-documents",
    });
    expect(capped.feed[0]?.state).toBe("Capped");
    const rejected = run("rejected");
    expect(rejected.modules).toEqual({
      kind: "none",
      title: "No module ran",
      text: "The run was rejected before it started, so there is nothing to show and nothing was spent.",
    });
    expect(rejected.alert?.alt).toBeNull();
    expect(rejected.alert?.action).toEqual({
      label: "Back to Documents",
      href: "#/run/start/documents",
    });
    expect(rejected.elapsed).toEqual({ value: null, note: "Rejected today at 14:37" });
    expect(rejected.spend.bar?.value).toBe(0);
    expect(rejected.feed.map((e) => e.state)).toEqual(["Rejected", "Queued"]);
    const interrupted = run("interrupted");
    expect(interrupted.alert?.action).toEqual({
      label: "Review and resume",
      href: "#/run/start/start",
    });
    expect(steps("interrupted")[5]).toMatchObject({ name: "Covenants", state: "Interrupted" });
    expect(interrupted.feed[0]?.state).toBe("Interrupted");
  });

  it("many modules, with two groups", () => {
    const r = run("many-modules");
    expect(r.spend.value).toBe("USD 11.85");
    expect(r.finished).toEqual({
      value: "12 of 22",
      bar: { label: "12 of 22 modules", value: 12, max: 22 },
    });
    const s = steps("many-modules");
    expect(s).toHaveLength(6);
    expect(r.labels).toEqual([
      "Full credit review",
      "As of Q3 FY2026",
      "Full credit review with every optional module and a late cut-off",
    ]);
    expect(r.feed).toHaveLength(6);
    expect(r.feed[4]).toMatchObject({
      who: "Credit agreement review",
      text: "Finished the review of the credit agreement and its latest amendment, then compared the stated leverage tests with the quarterly report and the segment data. Two tests were read from the amendment itself and one from its summary table, and each is stated with its period so a reader can see which was tested and when.",
    });
    expect(r.feed[5]).toMatchObject({
      who: "Business profile",
      text: "Stopped to wait for the model service, then carried on once it answered. The module that was waiting kept every figure it had already read, so nothing was read twice, and the time spent waiting counts in the elapsed time shown above, not in the spend. The run did not need to start the module again.",
    });
    const first = s[0];
    if (first?.kind !== "group") throw new Error("group");
    expect(first).toMatchObject({
      title: "12 modules finished",
      state: "Finished",
      showAll: "Show all 12",
    });
    expect(first.modules).toHaveLength(12);
    expect(first.modules[9]).toEqual({
      name: "Customer concentration",
      state: "Finished",
      detail: "Finished in 2 min 02 s, USD 0.70",
    });
    expect(first.modules.every((m) => m.state === "Finished")).toBe(true);
    expect(s[1]).toMatchObject({ kind: "module", name: "Recovery", state: "Running" });
    expect(s[4]).toMatchObject({
      kind: "module",
      name: "Environmental, social and governance factors, with supplier, customer and regulatory exposure",
      state: "Queued",
    });
    const last = s[5];
    if (last?.kind !== "group") throw new Error("group");
    expect(last).toMatchObject({
      title:
        "6 more modules queued, each one starting only once the module before it has finished running",
      showAll: "Show all 6",
    });
    expect(last.modules).toHaveLength(6);
  });

  it("none and unreadable", () => {
    expect(read().runs[9]).toEqual({ kind: "none", id: "none" });
    expect(read().runs[10]).toEqual({
      kind: "unreadable",
      id: "unreadable",
      issuer: "TransDigm Group",
      labels: ["Full credit review", "As of Q3 FY2026"],
      alert: {
        title: "Run activity cannot be read",
        text: "The run record could not be opened. This does not stop the run or change what it spends; the cap still applies.",
        action: { label: "Try again", href: "#/run/activity/unreadable" },
        alt: { label: "Back to the library", href: "#/" },
      },
    });
  });

  it("keeps null as null and zero as 0", () => {
    expect(run("queued").elapsed.value).toBeNull();
    expect(run("starting").finished.value).toBeNull();
    expect(run("queued").spend.bar?.value).toBe(0);
  });
});

describe("rejects, run activity", () => {
  it("a duplicate run id", () => {
    expect(reason(editRun("queued", ["id"], "running"))).toBe(
      "run.runs[1].id: expected an id no other run uses",
    );
  });
  it("a current that names no run, and a null current is read", () => {
    const source = structuredClone(fixture.slice) as { current: string | null };
    source.current = "nowhere";
    expect(reason(source)).toBe("run.current: expected null or the id of a run in this slice");
    source.current = null;
    expect(readSlice(source).kind).toBe("ok");
  });
  it("a started draft whose activity names no run", () => {
    expect(reason(edit("started", ["activity"], "nowhere"))).toBe(
      "run.drafts[6].activity: expected the id of a run in this slice",
    );
  });
  it.each(["https://example.com/", "javascript:alert(1)", "run/start"])("a link to %j", (href) => {
    expect(reason(editRun("finished", ["open", "href"], href))).toBe(
      'run.runs[3].open.href: expected an address starting with "#/"',
    );
  });
  it("an alert action with an outside address", () => {
    expect(reason(editRun("failed", ["alert", "alt", "href"], "http://x.test/"))).toBe(
      'run.runs[4].alert.alt.href: expected an address starting with "#/"',
    );
  });
  it("an unknown run state, record kind and module word", () => {
    expect(reason(editRun("running", ["state"], "Paused"))).toBe(
      "run.runs[0].state: expected one of Queued, Running, Finished, Failed, Capped, Rejected, Interrupted",
    );
    expect(reason(editRun("running", ["kind"], "other"))).toBe(
      "run.runs[0].kind: expected one of run, none, unreadable",
    );
    expect(reason(editRun("running", ["modules", "steps", 1, "state"], "Done"))).toBe(
      "run.runs[0].modules.steps[1].state: expected one of Queued, Running, Finished, Interrupted, Not assessable, Not run",
    );
    expect(reason(editRun("running", ["feed", 0, "state"], "Not run"))).toBe(
      "run.runs[0].feed[0].state: expected one of Queued, Running, Finished, Failed, Capped, Rejected, Interrupted, Not assessable",
    );
  });
  it("a module word a live run cannot carry", () => {
    expect(reason(editRun("running", ["modules", "steps", 6, "state"], "Not run"))).toBe(
      "run.runs[0].modules.steps[6].state: expected a module word a live run can carry",
    );
    expect(
      reason(editRun("many-modules", ["modules", "steps", 0, "modules", 2, "state"], "Not run")),
    ).toBe(
      "run.runs[8].modules.steps[0].modules[2].state: expected a module word a live run can carry",
    );
    expect(reason(editRun("many-modules", ["modules", "steps", 5, "state"], "Not run"))).toBe(
      "run.runs[8].modules.steps[5].state: expected a module word a live run can carry",
    );
  });
  it("a module word an ended run cannot carry", () => {
    expect(reason(editRun("failed", ["modules", "steps", 3, "state"], "Queued"))).toBe(
      "run.runs[4].modules.steps[3].state: expected a module word an ended run can carry",
    );
    expect(reason(editRun("finished", ["modules", "steps", 0, "state"], "Running"))).toBe(
      "run.runs[3].modules.steps[0].state: expected a module word an ended run can carry",
    );
  });
  it("starting outside a Running run and none outside a Rejected run", () => {
    expect(reason(editRun("queued", ["modules"], { kind: "starting", label: "x" }))).toBe(
      "run.runs[1].modules.kind: expected starting only in a Running run",
    );
    expect(reason(editRun("running", ["modules"], { kind: "none", title: "t", text: "x" }))).toBe(
      "run.runs[0].modules.kind: expected none only in a Rejected run",
    );
  });
  it("an empty group and a group inside a group", () => {
    expect(reason(editRun("many-modules", ["modules", "steps", 0, "modules"], []))).toBe(
      "run.runs[8].modules.steps[0].modules: expected a non-empty list",
    );
    const nested = {
      kind: "group",
      name: "Inner",
      state: "Finished",
      detail: null,
      title: "t",
      showAll: "s",
      modules: [{ name: "Hidden", state: "Finished", detail: null }],
    };
    expect(reason(editRun("many-modules", ["modules", "steps", 0, "modules"], [nested]))).toBe(
      "run.runs[8].modules.steps[0].modules[0]: expected a plain module, not a group",
    );
  });
  it("an ended run with a Queued member inside a group", () => {
    const group = {
      kind: "group",
      title: "t",
      state: "Finished",
      showAll: "s",
      modules: [{ name: "A", state: "Queued", detail: null }],
    };
    expect(reason(editRun("finished", ["modules", "steps", 0], group))).toBe(
      "run.runs[3].modules.steps[0].modules[0].state: expected a module word an ended run can carry",
    );
  });
  it("the first failing path in a record wins, in document order", () => {
    const s = structuredClone(fixture.slice) as { runs: Node[] };
    const run = s.runs[0] as { modules: { steps: Node[] }; feed: Node[] };
    run.modules.steps[6] = { ...run.modules.steps[6], state: "Not run" };
    run.feed[0] = { ...run.feed[0], state: "Bogus" };
    expect(reason(s)).toBe(
      "run.runs[0].modules.steps[6].state: expected a module word a live run can carry",
    );
    const t = structuredClone(fixture.slice) as { runs: Node[] };
    const r2 = t.runs[0] as { modules: { steps: Node[] }; feed: Node[] };
    r2.modules.steps[6] = { ...r2.modules.steps[6], name: "CP-3 X" };
    r2.feed[0] = { ...r2.feed[0], state: "Bogus" };
    expect(reason(t)).toBe("run.runs[0].modules.steps[6].name: expected no module code");
  });
  it("a module code anywhere in a run", () => {
    expect(reason(editRun("running", ["feed", 0, "text"], "CP-3 started."))).toBe(
      "run.runs[0].feed[0].text: expected no module code",
    );
    expect(reason(editRun("unreadable", ["alert", "text"], "Stopped at CP-12"))).toBe(
      "run.runs[10].alert.text: expected no module code",
    );
  });
  it("a missing figure value and a bad bar", () => {
    expect(reason(editRun("running", ["spend", "value"], undefined))).toBe(
      "run.runs[0].spend.value: expected a string or null",
    );
    expect(reason(editRun("running", ["spend", "bar", "value"], 21))).toBe(
      "run.runs[0].spend.bar.value: expected a number from 0 to max",
    );
  });
  it("an unreadable record with no alert", () => {
    expect(reason(editRun("unreadable", ["alert"], undefined))).toBe(
      "run.runs[10].alert: expected an object",
    );
  });

  describe("batch A reader rules", () => {
    it("a missing figure has no bar and says why; a value needs no bar to be shown", () => {
      const starting = readSlice(
        editRun("starting", ["finished"], { value: null, note: "Nothing yet", bar: null }),
      );
      expect(starting.kind).toBe("ok");
      const noBar = readSlice(
        editRun("running", ["spend"], { value: "USD 7.40", note: "No bar", bar: null }),
      );
      expect(noBar.kind).toBe("ok");
    });
    it("a missing figure with a bar is invalid", () => {
      expect(
        reason(editRun("starting", ["finished", "bar"], { label: "x", value: 0, max: 13 })),
      ).toBe("run.runs[2].finished.bar: expected null when the value is null");
    });
    it("ids are lower-case letters, digits and hyphens", () => {
      const want = "expected an id of lower-case letters, digits and hyphens";
      expect(reason(edit("purpose", ["id"], "pur/pose"))).toBe(`run.drafts[2].id: ${want}`);
      expect(reason(edit("documents", ["next"], "Purpose"))).toBe(`run.drafts[1].next: ${want}`);
      expect(reason(edit("confirm", ["previous"], ""))).toBe(`run.drafts[3].previous: ${want}`);
      expect(reason(edit("start", ["confirm", "started"], "a b"))).toBe(
        `run.drafts[5].confirm.started: ${want}`,
      );
      expect(reason(edit("started", ["activity"], ""))).toBe(`run.drafts[6].activity: ${want}`);
      expect(reason(editRun("running", ["id"], "Run 1"))).toBe(`run.runs[0].id: ${want}`);
      const s = structuredClone(fixture.slice) as { current: string };
      s.current = "";
      expect(reason(s)).toBe(`run.current: ${want}`);
    });
    it("a module code in any Run start string is invalid", () => {
      expect(reason(edit("start", ["recap", 0, "value"], "CP-3 and CP-4"))).toBe(
        "run.drafts[5].recap[0].value: expected no module code",
      );
      expect(reason(edit("purpose", ["purposes", 0, "modules"], "CP-2 to CP-5"))).toBe(
        "run.drafts[2].purposes[0].modules: expected no module code",
      );
    });
    it("a file name on the Documents step is the analyst's: CP-1.pdf reads ok", () => {
      const r = readSlice(edit("documents", ["files", 0, "name"], "CP-1.pdf"));
      expect(r.kind).toBe("ok");
      if (r.kind !== "ok") return;
      const docs = r.data.drafts.find((d) => d.id === "documents");
      if (docs?.step !== "documents") throw new Error("step");
      expect(docs.files[0]?.name).toBe("CP-1.pdf");
      // every other string of the file keeps the check
      expect(reason(edit("documents", ["files", 0, "kind"], "CP-1"))).toBe(
        "run.drafts[1].files[0].kind: expected no module code",
      );
    });
    it("started.activity names a run record", () => {
      expect(reason(edit("started", ["activity"], "none"))).toBe(
        "run.drafts[6].activity: expected the id of a run in this slice",
      );
    });
    it("a run with no steps or no feed lines is invalid", () => {
      expect(reason(editRun("finished", ["modules", "steps"], []))).toBe(
        "run.runs[3].modules.steps: expected a non-empty list",
      );
      expect(reason(editRun("finished", ["feed"], []))).toBe(
        "run.runs[3].feed: expected a non-empty list",
      );
    });
    it("an alert only on a failed, capped, rejected or interrupted run; open only on a finished one", () => {
      const alert = { title: "t", text: "x", action: { label: "a", href: "#/" }, alt: null };
      expect(reason(editRun("finished", ["alert"], alert))).toBe(
        "run.runs[3].alert: expected null unless the run is Failed, Capped, Rejected or Interrupted",
      );
      expect(reason(editRun("running", ["alert"], alert))).toBe(
        "run.runs[0].alert: expected null unless the run is Failed, Capped, Rejected or Interrupted",
      );
      expect(reason(editRun("failed", ["open"], { label: "Open", href: "#/" }))).toBe(
        "run.runs[4].open: expected null unless the run is Finished",
      );
    });
    it("structure is read before the module-code check", () => {
      const s = editRun("running", ["id"], undefined) as { runs: { feed: Node[] }[] };
      s.runs[0]?.feed.push({ who: "Run", time: "1", text: "CP-3 ran", state: "Queued" });
      expect(reason(s)).toBe("run.runs[0].id: expected a string");
    });
  });
});
