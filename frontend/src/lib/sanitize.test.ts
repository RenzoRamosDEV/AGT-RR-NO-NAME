import { describe, expect, it } from "vitest";
import { sanitizeError } from "./sanitize";

describe("sanitizeError", () => {
  it("returns null when there is nothing to show", () => {
    expect(sanitizeError(null)).toBeNull();
    expect(sanitizeError(undefined)).toBeNull();
    expect(sanitizeError("")).toBeNull();
    expect(sanitizeError(" \n\t\u0000 ")).toBeNull();
  });

  it("strips control characters and collapses whitespace", () => {
    expect(sanitizeError("a\u0000b\u001b[31m   c\n\nd")).toBe("a b [31m c d");
  });

  it("hides values that look like secrets", () => {
    expect(sanitizeError("boom token=abc123 en la llamada")).toBe(
      "boom token=[oculto] en la llamada",
    );
    expect(sanitizeError("API_KEY: xyz and password = hunter2")).toBe(
      "API_KEY: [oculto] and password = [oculto]",
    );
    expect(sanitizeError("401 con Bearer eyJhbGci.payload")).toBe("401 con Bearer [oculto]");
    expect(sanitizeError("clave sk-abcdefgh12345 rota")).toBe("clave [oculto] rota");
  });

  it("keeps ordinary text untouched", () => {
    expect(sanitizeError("Tiempo de espera agotado.")).toBe("Tiempo de espera agotado.");
  });

  it("truncates to the limit with an ellipsis", () => {
    const out = sanitizeError("x".repeat(500)) ?? "";
    expect(out).toHaveLength(200);
    expect(out.endsWith("…")).toBe(true);
    expect(sanitizeError("x".repeat(200))).toBe("x".repeat(200));
  });
});
