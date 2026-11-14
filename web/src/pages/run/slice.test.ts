import { readFileSync } from "node:fs";
import path from "node:path";
import { readSlice } from "./slice";

type Node = Record<string | number, unknown>;
const fixture = JSON.parse(
  readFileSync(path.join(import.meta.dirname, "../../../fixtures/run.json"), "utf8"),
) as { slice: unknown };
// A copy of the fixture slice with one draft's value at `at` replaced (undefined removes it).
function edit(id: string, at: (string | number)[], value: unknown): unknown {
  const copy = structuredClone(fixture.slice) as { drafts: Node[] };
  let node: Node = copy.drafts.find((d) => d.id === id) ?? {};
  for (const key of at.slice(0, -1)) node = node[key] as Node;
  const last = at[at.length - 1] ?? "";
  if (value === undefined) Reflect.deleteProperty(node, last);
  else node[last] = value;
  return copy;
}
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
    expect(docs.nextBlocked).toBe("Replace or remove the unreadable file to continue.");
    const purpose = by("purpose");
    if (purpose?.step !== "purpose") throw new Error("step");
    expect(purpose.chosen).toBe(purpose.purposes[0]?.id);
    expect(purpose.purposes[1]?.title).toBe("Earnings update");
    expect(purpose.purposes[1]?.modules).toBe("5 modules");
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
      "run.drafts[5].confirm.started: expected null or the id of a draft in this slice",
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
