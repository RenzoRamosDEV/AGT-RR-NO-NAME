---
name: change-hygiene
description: Revisa la higiene de un commit o PR - mensaje Conventional Commits (cabecera de 100 caracteres máximo), trazabilidad con OpenSpec, atomicidad, archivos que no deben subirse y cumplimiento de los hooks del repo. Úsalo al revisar commits, antes de un push o cuando falle commitlint, gitleaks o pre-commit.
allowed-tools: Read, Grep, Glob, Bash(git log:*), Bash(git show:*), Bash(git diff:*), Bash(git status:*), Bash(openspec:*), Bash(gitleaks:*)
---

# Higiene del cambio

Busca antes del push lo que rompe CI por descuido (cabecera larga, secreto de ejemplo,
variable obligatoria sin definir). Casos reales del repo: `references/history.md`.

## Mensaje del commit

- **Conventional Commits:** `tipo(ámbito opcional): descripción`. Los tipos válidos son los de
  `@commitlint/config-conventional`: `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`,
  `refactor`, `revert`, `style`, `test`.
- **Cabecera ≤ 100 caracteres** (`header-max-length`, valor por defecto de la configuración
  heredada en `.commitlintrc.json`). Cuéntalos: `git log -1 --format=%s | awk '{print length}'`.
  La regla `subject-case` está desactivada en ese archivo.
- El tipo describe el efecto: `feat` solo si cambia comportamiento observable; un cambio de
  tests es `test`, de tooling `chore`/`ci`.
- Los detalles van en el cuerpo, no en una cabecera interminable.
- El `type` no miente: un `fix` sin test que reproduzca el fallo es sospechoso.

## Trazabilidad con OpenSpec (regla del repo: todo cambio va por OpenSpec)

- Todo cambio, también mejoras, tests y tooling, pertenece a un change en
  `openspec/changes/<nombre>/` (o archivado en `openspec/changes/archive/`). Un commit
  suelto que cambia código sin change asociado es `IMPORTANTE`.
- Comprueba con `openspec list` / `openspec validate <change> --strict`.
- Si el cambio altera comportamiento observable, ¿hay delta spec en `specs/`? Si no
  (`skip_specs: true`), ¿es cierto que no cambia comportamiento?
- ¿Las tareas de `tasks.md` marcadas `[x]` corresponden a lo que el diff hace de verdad?
- Un change terminado se archiva (`openspec archive <n> --yes`); no se deja a medias.

## Atomicidad

- Un commit que **por sí solo** deja CI o tests en rojo (necesita el commit siguiente para
  pasar) es bloqueante si está `CONFIRMADO` (con `gh run list --commit <sha>` o el
  mismo fallo reproducido); si solo es mezcla de propósitos sin romper nada, menor.
- Un commit = un propósito. Mezclar refactor + feature + formateo oculta regresiones.
- ¿El commit deja el repo en verde por sí solo (lint, tests, tipos)? Un commit que solo
  pasa con el siguiente complica `git bisect`.
- Lockfiles (`uv.lock`, `pnpm-lock.yaml`) cambian con su manifiesto, no solos.

## Contenido que no debe subirse

- Secretos y credenciales, incluidos los "de ejemplo": en documentación usa variables
  (`$INGEST_TOKEN`) y no valores literales en cabeceras de `curl`. Cambios sin
  commitear: `gitleaks protect --staged --no-banner -v`; commits ya hechos:
  `gitleaks detect --no-banner --log-opts="<base>..<sha>"`.
- Binarios, capturas, volcados, `.env`, `mutants/`, `.coverage`, `__pycache__`, `.venv`.
- Rutas absolutas de la máquina del autor, correos o nombres personales en el contenido.

## Hooks y puertas del repo

Los hooks de pre-commit son ruff, ruff-format, mypy, import-linter, biome y gitleaks; el
CI añade commitlint, osv-scanner, hadolint, Docker smoke y la suite de tests. Un commit hecho
con `--no-verify` o un cambio que desactiva una regla para "pasar" es `IMPORTANTE` salvo
justificación escrita (ADR o comentario con el motivo).

## En CI

Si el cambio toca `.github/workflows/`: acciones fijadas por **SHA completo** con el tag en
comentario; verifica cada tag con el objeto exacto (un prefijo como `v2` puede no existir y
un ref inválido en un workflow reutilizable invalida todo el run).
