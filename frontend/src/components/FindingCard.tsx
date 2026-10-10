import { useEffect, useState } from "react";
import type { Finding } from "../data/mock";
import { copyText } from "../lib/clipboard";
import {
  type SeverityLevel,
  findingFile,
  findingLine,
  severityLabel,
  severityLevel,
} from "../lib/findings";
import { splitRecommendation } from "../lib/recommendation";
import { Collapsible, FINDING_LIMIT, isLong } from "./Collapsible";
import { Markdown } from "./Markdown";
import {
  AlertIcon,
  CheckCircleIcon,
  CopyIcon,
  DotCircleIcon,
  FileIcon,
  InfoIcon,
  XCircleIcon,
} from "./icons";
import { AgentAvatar, agentLabel } from "./ui/AgentAvatar";

const ICON: Record<SeverityLevel, typeof AlertIcon> = {
  danger: XCircleIcon,
  warning: AlertIcon,
  info: InfoIcon,
  neutral: DotCircleIcon,
};

/** `archivo:línea` as a chip with a button that copies it; the result is announced as text. */
function LocationChip({ text, label }: { text: string; label: string }) {
  const [result, setResult] = useState<"idle" | "ok" | "fail">("idle");
  useEffect(() => {
    if (result === "idle") return;
    const timer = setTimeout(() => setResult("idle"), 2000);
    return () => clearTimeout(timer);
  }, [result]);
  return (
    <span className="loc-chip">
      <FileIcon size={13} />
      <span className="mono">{text}</span>
      <button
        type="button"
        className="loc-copy"
        aria-label={`Copiar ${label} ${text}`}
        title="Copiar ubicación"
        onClick={async () => setResult((await copyText(text)) ? "ok" : "fail")}
      >
        {result === "ok" ? <CheckCircleIcon size={13} /> : <CopyIcon size={13} />}
      </button>
      <output className="sr-only">
        {result === "ok" ? "Copiado" : result === "fail" ? "No se pudo copiar" : ""}
      </output>
    </span>
  );
}

/**
 * One finding as a card: colored severity with an icon, where it is (`archivo:línea`, only when it
 * has a file), the message with a little formatting and, when the text carries a label such as
 * `Arreglo:`, the advice apart. `showFile` is off under a heading that already names the file.
 */
export function FindingCard({
  id,
  finding,
  agent,
  showFile = true,
}: {
  id: string;
  finding: Finding;
  /** The agent that found it, shown when findings of several agents are mixed. */
  agent?: string;
  showFile?: boolean;
}) {
  const level = severityLevel(finding.severity);
  const Icon = ICON[level];
  const file = findingFile(finding);
  const line = findingLine(finding);
  const { body, recommendation } = splitRecommendation(finding.message);
  const where = file ? (line ? `${file}:${line}` : file) : undefined;
  // Under a heading that names the file only the line is left, and only if there is a file.
  const location = showFile ? where : file && line ? `L${line}` : undefined;
  return (
    <div className="finding-card" data-level={level} data-severity={finding.severity.toLowerCase()}>
      <header className="finding-head">
        <span className="sev">
          <Icon size={14} />
          <span className="sev-label">{severityLabel(finding.severity)}</span>
        </span>
        {location && <LocationChip text={location} label={showFile ? "ubicación" : "línea"} />}
        {agent && (
          <span className="finding-agent">
            <AgentAvatar agent={agent} size={16} />
            {agentLabel(agent)}
          </span>
        )}
      </header>
      {body && (
        <Collapsible id={`finding:${id}`} long={isLong(body, FINDING_LIMIT)}>
          <Markdown text={body} className="finding-text" />
        </Collapsible>
      )}
      {recommendation && (
        <div className="finding-reco">
          <strong className="reco-label">Arreglo sugerido</strong>
          <Markdown text={recommendation} />
        </div>
      )}
    </div>
  );
}
