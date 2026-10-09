# Seguridad

Duelo es un proyecto personal de portafolio que corre en local; no hay
multi-usuario ni datos de terceros en juego. Aun así:

- **Secretos**: nunca van en el repo. `gitleaks` corre en pre-commit y en CI
  (job `gitleaks`) sobre cada cambio. Si gitleaks bloquea un commit por un
  falso positivo, no se desactiva el hook - se ajusta la regla.
- **Dependencias**: `osv-scanner` corre en CI (jobs `osv-scan` / `osv-scan-pr`)
  sobre `backend/uv.lock` y `frontend/pnpm-lock.yaml`. Renovate
  (`renovate.json`) mantiene las versiones al día una vez instalada la
  GitHub App.
- **Agentes de review**: Claude Code y Codex corren siempre en modo
  solo-lectura (sin `Edit`/`Write`/`Bash` para Claude, `--sandbox read-only`
  para Codex) y nunca ven el diff si `gitleaks` detecta un secreto en él.

## Reportar un problema

Al ser un proyecto personal sin usuarios externos, no hay un proceso formal
de disclosure. Si encuentras algo, abre un issue en este repositorio.
