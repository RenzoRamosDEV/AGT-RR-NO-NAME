import { describe, expect, it } from "vitest";
import { updatedAgo } from "./liveness";

describe("updatedAgo", () => {
  it.each([
    [0, "Actualizado ahora"],
    [4.9, "Actualizado ahora"],
    [5, "Actualizado hace 5 s"],
    [59.9, "Actualizado hace 59 s"],
    [60, "Actualizado hace 1 min"],
    [3599, "Actualizado hace 59 min"],
    [3600, "Actualizado hace 1 h"],
    [7300, "Actualizado hace 2 h"],
  ])("%s s → %s", (seconds, text) => expect(updatedAgo(seconds)).toBe(text));
});
