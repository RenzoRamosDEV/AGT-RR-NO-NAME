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

  it("hides the token after the scheme of an Authorization header", () => {
    // Regression: `Authorization: Bearer abc` hid only the word "Bearer" and left the token.
    expect(sanitizeError("cabecera Authorization: Bearer eyJhbGci.payload fin")).toBe(
      "cabecera Authorization: [oculto] fin",
    );
    expect(sanitizeError("Authorization: Bearer abc123tokenvalue")).toBe("Authorization: [oculto]");
    expect(sanitizeError("Authorization: Basic dXNlcjpwYXNz")).toBe("Authorization: [oculto]");
    expect(sanitizeError("Authorization: Bearer abc123tokenvalue")).not.toContain("abc123");
  });

  it("hides credentials with a recognisable shape, like the backend does", () => {
    const github = `ghp_${"a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5"}`;
    expect(sanitizeError(`token de GitHub ${github}`)).toBe("token de GitHub [oculto]");
    expect(sanitizeError("clave AKIAIOSFODNN7EXAMPLE en el diff")).toBe(
      "clave [oculto] en el diff",
    );
    expect(sanitizeError("webhook xoxb-123456789012-abcdefghij")).toBe("webhook [oculto]");
    // Split up: a whole JWT in the source would trip the secret scanner.
    const jwt = ["eyJhbGciOiJIUzI1NiJ9", "eyJzdWIiOiIxMjM0In0", "c2lnbmF0dXJl"].join(".");
    expect(sanitizeError(`jwt ${jwt} fin`)).toBe("jwt [oculto] fin");
    expect(
      sanitizeError(
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA\n-----END RSA PRIVATE KEY-----",
      ),
    ).toBe("[oculto]");
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
