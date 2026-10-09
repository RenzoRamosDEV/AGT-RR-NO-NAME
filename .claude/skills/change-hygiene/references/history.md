# Fallos reales de este repo que esta skill previene

No se carga por defecto; sirve de contexto cuando haga falta justificar una regla.

- `69b1081`: cabecera de commit de 117 caracteres → `commitlint` en rojo (límite 100).
- README con `curl -H "X-Ingest-Token: <valor literal>"` → `gitleaks` bloqueó el commit
  (`curl-auth-header`). Los ejemplos usan variables de entorno.
- `ef2ceec`: el contenedor pasó a exigir `INGEST_TOKEN` y el smoke test de CI lo arrancaba
  sin la variable → `docker-build-smoke` en rojo hasta `fce3e3a`.
- Un tag de Action que no existía como objeto exacto (`@v2` por prefijo) invalidó el run
  entero de CI. Se verifica con `git ls-remote --tags`.
- Una sesión de SQLAlchemy compartida entre dos repositorios hizo fallar `session.begin()`;
  solo lo destapó el test E2E.
