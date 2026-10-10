# Design

## Context

Ver `proposal.md`. Estado observado:

- `review_payload.py` tiene las instrucciones inline (`_INSTRUCTIONS`, con `{mark}` para el
  nonce) y `build_prompt(change, nonce=None)` las concatena con los bloques `DATOS-{mark}` y
  `DIFF-{mark}`. Lo cubren `tests/unit/adapters/test_review_payload.py` (datos, delimitación,
  nonce aleatorio, recortes) y los tests de los adaptadores, que no inspeccionan el texto.
- `prompts/review/` existe en la raíz con un `.gitkeep`: la spec (`docs/spec/duelo.md`) prevé
  `prompts/review/v{n}.md` como «prompts como código». El `Dockerfile` solo copia `backend/src`,
  pero la imagen es de la API y del worker `platform`, que nunca construyen un prompt; el worker
  `agents` corre desde el repositorio (`just worker`).
- Claude revisa con `Read/Grep/Glob` confinado a la carpeta del proyecto; Codex no tiene
  herramientas ni acceso al repo (`uses_project_folder = False`). Ambos devuelven el mismo JSON
  (`REVIEW_SCHEMA`), validado y acotado.
- `code-guardian` (`.claude/agents/`), `/guardian` (`.claude/skills/guardian`, `context: fork`),
  el hook `.claude/hooks/guardian-readonly.py` (con test en `backend/tests/unit/tooling/`) y 14
  skills de análisis forman el flujo de revisión del desarrollador; `CONTRIBUTING.md`,
  `codex_cli.py` (comentario) y `docs/temporal-buenas-practicas.md` los citan.

## Goals / Non-Goals

**Goals:**
- Un único criterio de revisión, versionado y legible, que reciben los dos agentes.
- Sin cambiar el contrato JSON ni el almacenamiento.
- `.claude/` queda solo con las skills de OpenSpec.

**Non-Goals:**
- `prompt_version` en la tabla `reviews` y el filtro de estadísticas por versión (otro change;
  hoy ninguna review guarda qué prompt la produjo).
- Dar a Codex acceso al repositorio o cambiar permisos de los CLI.
- Añadir `confidence` al JSON (obligaría a tocar dominio, API y frontend): la confianza se
  expresa con la regla «solo confirmado o probable; lo demás, dudas en el resumen».

## Decisions

1. **El fichero contiene todas las instrucciones**, incluido el bloque de seguridad con
   `{mark}` y el «cómo rellenar el JSON»; `review_payload.py` solo lo carga, sustituye `{mark}`
   y añade los bloques de datos. Así un cambio de criterio es un diff en Markdown sin tocar
   Python. Alternativa: dejar seguridad y formato en código y versionar solo «qué buscar»;
   descartada porque parte del criterio (qué es un hallazgo, la rúbrica) está entrelazada con el
   formato.

2. **Carga desde la raíz del repositorio** (`Path(__file__).resolve().parents[5] / "prompts" /
   "review" / f"{PROMPT_VERSION}.md"`), perezosa y cacheada (`functools.cache`), con
   `FileNotFoundError` que nombra la ruta. `build_prompt` admite `instructions=` para los tests
   y para quien quiera inyectar otro texto. Alternativa: `importlib.resources` con el fichero
   dentro del paquete; descartada porque la spec y la documentación fijan `prompts/review/` en
   la raíz y el único proceso que lo lee corre desde el repo.

3. **Contenido de `v2.md`**: criterio de `code-guardian` sin lo específico de Duelo, en español,
   ~100 líneas: rol y objetivo; prioridades; qué buscar por familia (condiciones y límites,
   nulos y tipos, errores y recursos, estado y concurrencia, contratos; secretos, inyección,
   salida sin escapar, validación de entrada, auth, fugas en logs, cadena de suministro; lo
   eliminado, cambios de firma, coherencia con el mensaje, archivos que no deberían estar);
   evidencia (localizar, trazar, refutar; con herramientas, verificar en el repo; sin ellas,
   solo lo que se ve en el diff); qué NO reportar (formato, lo que un linter atrapa, olores sin
   camino, patrones que un spec o ADR explica); rúbrica 0–3 / 4–6 / 7–10 con la lista de
   bloqueantes e importantes; severidades con definición; formato del JSON (como hoy) y
   «máximo 10 hallazgos, uno por defecto aunque se repita»; bloque de datos no confiables.
   La rúbrica usa el mismo criterio determinista de `review-report` para que la nota signifique
   lo mismo en los dos agentes.

4. **Borrado completo del flujo de Claude Code.** Se eliminan agente, comando, hook, test del
   hook y las 15 skills de revisión; se conservan `openspec-*` y la carpeta `.claude/commands`
   si no contiene nada del guardian. `CONTRIBUTING.md` pasa a describir que las reviews del
   producto siguen `prompts/review/v2.md` y que el desarrollador revisa con las herramientas
   del repo (`just ci`). Alternativa: dejar las skills «por si acaso»; descartada por petición
   expresa (criterio en un solo sitio).

5. **Tests.** Unitarios en `test_review_payload.py`: el prompt sale del fichero versionado
   (inyectando `instructions=` distinto cambia el prompt; sin inyectar, contiene un fragmento
   del v2), el fichero v2 existe y no tiene `{mark}` sin sustituir tras construir, y la rúbrica
   y la regla de evidencia están presentes (frases concretas). Los tests actuales de
   delimitación y nonce siguen tal cual.

## Risks / Trade-offs

- [Un prompt largo gasta contexto y tiempo del CLI] → ~100 líneas (~1 500 tokens) frente a
  60 000 caracteres de diff: marginal. El plazo del agente no cambia.
- [Los modelos puntúan distinto aunque la rúbrica sea la misma] → es lo que mide el duelo; la
  rúbrica reduce la dispersión, no la elimina.
- [Se pierde la guía específica del repo que había en las skills] → asumido (proposal);
  las reglas binding siguen en `openspec/config.yaml`, ADR y docs.
- [Reviews antiguas y nuevas no se distinguen en estadísticas] → pendiente de
  `prompt_version` (non-goal explícito).

## Migration Plan

Sin migración de datos. Al desplegar, reiniciar el worker `agents`; las reviews nuevas usan v2.
Rollback: volver al commit anterior (el prompt v1 inline vuelve con él).
