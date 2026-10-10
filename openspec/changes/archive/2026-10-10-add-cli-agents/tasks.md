# Tasks

## 1. Runner de subprocesos

- [x] 1.1 `subprocess_runner.run_command` acepta `input` (stdin), `exclude_env` y `max_output_bytes`; tests: stdin llega al hijo, las variables excluidas no llegan, la salida se acota y el plazo mata el grupo

## 2. Esquema, prompt y parseo

- [x] 2.1 `adapters/agents/review_payload.py`: esquema JSON de la review, `build_prompt(change)` (datos delimitados con marca aleatoria, recorte a 60 000 con aviso) y `parse_review_payload` (tipos, rangos, límites, `file` vacío → «N/A»); tests unitarios incluido el diff malicioso y los valores límite

## 3. Agentes

- [x] 3.1 `adapters/agents/cli_common.py`: jerarquía `CliAgentError` con mensajes fijos, detección de sesión no iniciada, entorno filtrado, directorio de trabajo (ruta del proyecto o temporal 0700), log estructurado de cada ejecución, semáforo compartido
- [x] 3.2 `ClaudeCliAgent`: argumentos de solo lectura exactos, prompt por stdin, parseo de `structured_output`/`result`, `is_error`, plazo; tests con runner falso
- [x] 3.3 `CodexCliAgent`: argumentos de solo lectura exactos, esquema y salida en un directorio temporal 0700/0600 borrado siempre, prompt por stdin, lectura del fichero de `-o`; tests con runner falso
- [x] 3.4 Test de integración opcional con los CLI reales (`RUN_CLI_AGENT_TESTS=1`, salta si falta el binario o la variable)

## 4. Composición

- [x] 4.1 `config.py`: `AGENT_TIMEOUT_SECONDS` (< 300), `AGENT_MAX_CONCURRENCY`, `CLAUDE_BIN`, `CODEX_BIN`, `CLAUDE_MODEL`, `CODEX_MODEL`, tope de presupuesto de Claude; validadores y tests
- [x] 4.2 Puerto `ProjectPaths` y `SqlAlchemyProjectRepository.path_of`; test de integración con Postgres
- [x] 4.3 `adapters/agents/registry.py` (`build_agents`) y `worker.py`: registro por nombre sin distinguir mayúsculas, `max_concurrent_activities` en la queue `agents` solo con agentes reales; tests del registro y del worker

## 5. Documentación y cierre

- [x] 5.1 README, `docs/architecture.md`, `docs/testing.md` y las frases de `docs/flujo-duelo.html` que digan «solo existe FakeAgent»: cómo activarlo (`AGENT_NAMES=claude,codex`), requisitos (sesión en ambos CLI), qué hace y qué NO hace, consumo, solo lectura
- [x] 5.2 `just lint`, `just test` y `just ci` en verde; `just mutation` si se tocan `domain/` o `application/`; `openspec validate add-cli-agents`
