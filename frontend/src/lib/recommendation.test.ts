import { describe, expect, it } from "vitest";
import { splitRecommendation } from "./recommendation";

describe("splitRecommendation", () => {
  it("returns the whole text as the body when there is no label", () => {
    expect(splitRecommendation("  La contraseña queda expuesta.  ")).toEqual({
      body: "La contraseña queda expuesta.",
      recommendation: undefined,
    });
  });

  it("separates the advice after `Arreglo:`", () => {
    expect(splitRecommendation("Credencial en el código. Arreglo: cárgala del entorno.")).toEqual({
      body: "Credencial en el código.",
      recommendation: "cárgala del entorno.",
    });
  });

  it("understands the other labels, with or without accents and in English", () => {
    for (const label of ["Sugerencia", "Recomendación", "Recomendacion", "Fix", "Suggestion"]) {
      expect(splitRecommendation(`Problema. ${label}: haz esto`).recommendation).toBe("haz esto");
    }
  });

  it("accepts the label in bold and on its own line", () => {
    expect(splitRecommendation("Problema\n**Arreglo:** usa una constante")).toEqual({
      body: "Problema",
      recommendation: "usa una constante",
    });
  });

  it("only splits where the label opens a sentence", () => {
    const message = "El prefijo fix: del commit no aclara nada";
    expect(splitRecommendation(message)).toEqual({ body: message, recommendation: undefined });
  });

  it("keeps the first label when there are several", () => {
    expect(splitRecommendation("A. Arreglo: uno. Sugerencia: dos")).toEqual({
      body: "A.",
      recommendation: "uno. Sugerencia: dos",
    });
  });

  it("returns an empty body when the text is only advice", () => {
    expect(splitRecommendation("Arreglo: rota la clave")).toEqual({
      body: "",
      recommendation: "rota la clave",
    });
  });

  it("ignores a label with no advice after it", () => {
    expect(splitRecommendation("Texto. Arreglo:")).toEqual({
      body: "Texto.",
      recommendation: undefined,
    });
  });
});
