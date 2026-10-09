import { useEffect, useState } from "react";
import { copyText } from "../lib/clipboard";
import { Button } from "./ui/Button";

type Result = "idle" | "ok" | "fail";

const MESSAGE: Record<Result, string> = { idle: "", ok: "Copiado", fail: "No se pudo copiar" };

/** Copy-to-clipboard button; the outcome is announced as text in a live region. */
export function CopyButton({ label, value }: { label: string; value: string }) {
  const [result, setResult] = useState<Result>("idle");

  useEffect(() => {
    if (result === "idle") return;
    const timer = setTimeout(() => setResult("idle"), 2500);
    return () => clearTimeout(timer);
  }, [result]);

  return (
    <span className="copy">
      <Button onClick={async () => setResult((await copyText(value)) ? "ok" : "fail")}>
        {label}
      </Button>
      <output className="muted">{MESSAGE[result]}</output>
    </span>
  );
}
