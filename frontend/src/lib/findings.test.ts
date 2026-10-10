import { describe, expect, it } from "vitest";
import { makeFinding, makeReview } from "../test/fixtures";
import {
  findingFile,
  findingLine,
  findingLocation,
  groupFindings,
  severityLabel,
  severityLevel,
  severityRank,
  severityTone,
} from "./findings";

describe("severityRank", () => {
  it("orders known severities and sends unknown ones last", () => {
    expect(severityRank("critical")).toBeLessThan(severityRank("HIGH"));
    expect(severityRank("info")).toBeLessThan(severityRank("nit"));
    expect(severityRank("nit")).toBeLessThan(severityRank("something else"));
  });

  it("knows the backend's own severities, most serious first", () => {
    const order = ["bug", "risk", "improvement", "nit"].map(severityRank);
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });
});

describe("severityTone", () => {
  it.each([
    ["critical", "danger"],
    ["BUG", "danger"],
    ["high", "danger"],
    ["risk", "warning"],
    ["medium", "warning"],
    ["improvement", "neutral"],
    ["nit", "neutral"],
    ["whatever", "neutral"],
  ] as const)("%s is %s", (severity, tone) => {
    expect(severityTone(severity)).toBe(tone);
  });
});

describe("groupFindings", () => {
  it("returns no groups without findings", () => {
    expect(groupFindings([makeReview(), makeReview({ findings: [] })])).toEqual([]);
  });

  it("puts findings of different agents in the same file group, most severe first", () => {
    const groups = groupFindings([
      makeReview({
        agent: "claude",
        findings: [makeFinding({ file: "a.py", severity: "low", line: 1, message: "low" })],
      }),
      makeReview({
        agent: "codex",
        findings: [makeFinding({ file: "a.py", severity: "high", line: 9, message: "high" })],
      }),
    ]);
    expect(groups).toHaveLength(1);
    expect(groups[0].findings.map((f) => [f.message, f.agent])).toEqual([
      ["high", "codex"],
      ["low", "claude"],
    ]);
  });

  it("orders by line within the same severity and by file between groups", () => {
    const groups = groupFindings([
      makeReview({
        findings: [
          makeFinding({ file: "b.py", line: 2 }),
          makeFinding({ file: "a.py", line: 7, message: "later" }),
          makeFinding({ file: "a.py", line: 3, message: "earlier" }),
        ],
      }),
    ]);
    expect(groups.map((g) => g.file)).toEqual(["a.py", "b.py"]);
    expect(groups[0].findings.map((f) => f.message)).toEqual(["earlier", "later"]);
  });

  it("gives every finding a unique key even when two reviews report the same thing", () => {
    const same = [makeFinding()];
    const groups = groupFindings([makeReview({ findings: same }), makeReview({ findings: same })]);
    const keys = groups[0].findings.map((f) => f.key);
    expect(new Set(keys).size).toBe(2);
  });
});

// Regresión: el FakeAgent envía `file: "N/A"` y `line: 0`, y el panel mostraba `N/A` y `L0`.
describe("findings without a location", () => {
  it("treats an empty or N/A file and a non-positive line as unknown", () => {
    expect(findingFile({ file: "N/A" })).toBeUndefined();
    expect(findingFile({ file: " n/a " })).toBeUndefined();
    expect(findingFile({ file: "" })).toBeUndefined();
    expect(findingFile({ file: " src/a.py " })).toBe("src/a.py");
    expect(findingLine({ line: 0 })).toBeUndefined();
    expect(findingLine({ line: -3 })).toBeUndefined();
    expect(findingLine({ line: 1.5 })).toBeUndefined();
    expect(findingLine({ line: 12 })).toBe(12);
  });

  it("builds file:line, file or nothing", () => {
    expect(findingLocation(makeFinding({ file: "a.py", line: 4 }))).toBe("a.py:4");
    expect(findingLocation(makeFinding({ file: "a.py", line: 0 }))).toBe("a.py");
    expect(findingLocation(makeFinding({ file: "N/A", line: 0 }))).toBeUndefined();
  });

  it("groups unlocated findings together and always last, keeping severity order", () => {
    const groups = groupFindings([
      makeReview({
        findings: [
          makeFinding({ file: "N/A", line: 0, severity: "low", message: "sin sitio bajo" }),
          makeFinding({ file: "z.py", line: 5, message: "z" }),
          makeFinding({ file: "", line: 0, severity: "high", message: "sin sitio alto" }),
        ],
      }),
    ]);
    expect(groups.map((g) => g.file)).toEqual(["z.py", undefined]);
    expect(groups[1].findings.map((f) => f.message)).toEqual(["sin sitio alto", "sin sitio bajo"]);
  });

  it("puts findings without a line after those with one at the same severity", () => {
    const [group] = groupFindings([
      makeReview({
        findings: [
          makeFinding({ file: "a.py", line: 0, message: "sin línea" }),
          makeFinding({ file: "a.py", line: 40, message: "con línea" }),
        ],
      }),
    ]);
    expect(group.findings.map((f) => f.message)).toEqual(["con línea", "sin línea"]);
  });
});

describe("severityLevel and severityLabel", () => {
  it("gives the backend's four severities their own color family", () => {
    expect(["bug", "risk", "improvement", "nit"].map(severityLevel)).toEqual([
      "danger",
      "warning",
      "info",
      "neutral",
    ]);
  });

  it("is case insensitive and treats an unknown severity as neutral", () => {
    expect(severityLevel("BUG")).toBe("danger");
    expect(severityLevel("whatever")).toBe("neutral");
  });

  it("names severities in Spanish and keeps an unknown one as written", () => {
    expect(["bug", "risk", "improvement", "nit"].map(severityLabel)).toEqual([
      "Bug",
      "Riesgo",
      "Mejora",
      "Detalle",
    ]);
    expect(severityLabel("seguridad")).toBe("Seguridad");
    expect(severityLabel("")).toBe("—");
  });
});
