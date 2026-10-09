# Tasks

## 1. Límites y validación en `Change`

- [x] 1.1 Añadir constantes de límite y validación en `domain/change.py` (`head_sha` vacío /
      > 64 / NUL, `ref` > 255, `url` > 1000, NUL en identificadores → `ValueError` que
      nombra el campo) y recorte de `title` (500) y `author` (255); verificar con tests
      unitarios parametrizados de particiones de equivalencia (válido / vacío / demasiado
      largo / NUL) y valores límite (n-1, n, n+1) para cada campo, incluido que el recorte
      conserva el prefijo original.
- [x] 1.2 Test de guarda: las constantes del dominio coinciden con las longitudes de
      `ChangeModel` y `ReviewModel`; verificar que falla si se cambia una de las dos (se
      comprueba a mano alterando una constante y restaurándola).

## 2. Nombre de agente en `Review`

- [x] 2.1 Validar el nombre de agente (vacío o > 50 → `ValueError`) en `Review.succeeded` y
      `Review.failed`; verificar con tests de valores límite (0, 1, 50, 51 caracteres) y
      que ambos constructores rechazan igual.

## 3. Saneado de NUL en persistencia

- [x] 3.1 Añadir `hypothesis` como dependencia de desarrollo y crear
      `adapters/persistence/sanitize.py` (`sanitize_text`, `sanitize_json`); verificar con
      tests de propiedades: el resultado nunca contiene NUL, es idempotente, no cambia
      las cadenas sin NUL, y `sanitize_json` conserva la estructura (mismas claves y
      longitudes de lista).
- [x] 3.2 Aplicar el saneado en `SqlAlchemyChangeRepository` (`title`, `author`, `diff`) y
      `SqlAlchemyReviewRepository` (`summary`, `raw_output`, `error`, `findings`);
      verificar con los tests unitarios de sesión mockeada ya existentes más uno por
      repositorio que comprueba que lo enviado a la sesión no contiene NUL.

## 4. Verificación con Postgres real

- [x] 4.1 Test de integración con testcontainers de los bordes: cada campo en su límite
      máximo se persiste y se lee de vuelta íntegro; `title` y `author` por encima se
      guardan recortados; NUL en `title`/`author`/`diff` y en `summary`/`error`/`findings`
      se guarda con `U+FFFD`; verificar que ningún caso produce un error de base de datos.
- [x] 4.2 Tests de regresión de lo que ya funcionaba y no debe romperse: diff de 5 MB,
      comillas e intento de inyección SQL guardados como texto literal y Unicode/emoji
      ida y vuelta intactos.
- [ ] 4.3 Verificación final: `just ci` en verde y CI real de GitHub en verde.

## Workflow follow-up

- Archivar con `openspec archive harden-input-limits --yes` tras mergear, para que los
  requisitos nuevos se fundan en `change-ingestion` y `change-review`.
