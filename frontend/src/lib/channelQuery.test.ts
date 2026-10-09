import { describe, expect, it } from "vitest";
import { statusesFor } from "./channelQuery";

describe("statusesFor", () => {
  it("sends nothing for all", () => {
    expect(statusesFor("all")).toBeUndefined();
  });

  it("maps each filter to the backend states", () => {
    expect(statusesFor("running")).toEqual(["pending", "running"]);
    expect(statusesFor("failed")).toEqual(["failed", "partial_failed"]);
    expect(statusesFor("completed")).toEqual(["completed"]);
  });
});
