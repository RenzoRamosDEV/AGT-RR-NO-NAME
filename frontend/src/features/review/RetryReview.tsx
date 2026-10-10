import { type FormEvent, useId, useState } from "react";
import { Busy } from "../../components/Busy";
import { Button } from "../../components/ui/Button";
import { useDataSource } from "../../data/source";
import { ApiError } from "../../lib/api";
import { clearIngestToken, useIngestToken } from "../../lib/ingestToken";

interface Props {
  changeId: string;
  /** Called with a message to announce when the retry was accepted or is no longer possible. */
  onSettled: (message: string) => void;
}

function failureMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Ocurrió un error inesperado.";
  switch (error.status) {
    case 401:
      return "Token de ingesta no válido.";
    case 404:
      return "Change no encontrado.";
    case 503:
      return "El orquestador no está disponible. Inténtalo de nuevo en unos minutos.";
    case null:
      return error.message;
    default:
      return `No se pudo reintentar: ${error.message}`;
  }
}

/**
 * Retry form for a change whose review failed. The token is typed by the user and kept in memory
 * only (see `lib/ingestToken`); a 401 forgets it.
 */
export function RetryReview({ changeId, onSettled }: Props) {
  const source = useDataSource();
  const [token, setToken] = useIngestToken();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tokenId = useId();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (sending) return;
    const value = token.trim();
    if (!value) {
      setError("Introduce el token de ingesta para reintentar.");
      return;
    }
    setSending(true);
    setError(null);
    try {
      const result = await source.retry(changeId, value);
      onSettled(`Reintento en marcha (run ${result.run}).`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        onSettled("Esta review ya no se puede reintentar: su estado cambió.");
      } else {
        if (e instanceof ApiError && e.status === 401) clearIngestToken();
        setError(failureMessage(e));
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="retry" onSubmit={submit}>
      <label htmlFor={tokenId}>Token de ingesta</label>
      <input
        id={tokenId}
        className="search"
        type="password"
        autoComplete="off"
        value={token}
        onChange={(e) => setToken(e.target.value)}
      />
      <Button type="submit" disabled={sending}>
        {sending ? <Busy activity="retry" label="Reintentando…" inline /> : "Reintentar review"}
      </Button>
      {error && (
        <p className="notice" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
