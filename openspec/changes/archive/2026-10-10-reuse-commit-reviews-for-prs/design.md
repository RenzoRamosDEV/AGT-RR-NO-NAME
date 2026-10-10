# Design

## Contexto

`_ingest` (application/ingest_commit.py) persiste el change con `ChangeRepository.add` y luego llama
a `ReviewStarter.start`. La PR y el commit con el mismo SHA son changes distintos por la restricción
`uq_changes_natural_key (project_id, kind, head_sha)`. Las reviews ya son idempotentes por
`uq_reviews_natural_key (change_id, agent, run)`.

## Decisiones

1. **La decisión es una función pura en `domain`** (`domain/review_reuse.py::reviews_to_reuse`).
   Recibe la PR, el commit candidato con sus reviews, los nombres de agente esperados y `now`, y
   devuelve las copias (`Review` nuevas con `reused_from_change_id`) o una tupla vacía. Reutiliza solo si:
   la PR es `pr`, el origen es `commit` del mismo proyecto y SHA, el diff y `diff_truncated` son
   idénticos, y hay una review `completed` del `run` actual del origen por cada nombre esperado
   (comparación exacta; las de agentes no esperados se ignoran). El diff se compara tal cual: si el
   de la PR llevara NUL (que el repositorio sanea al guardar) no coincidiría y se revisaría con
   normalidad, que es el lado seguro.
2. **Búsqueda del origen**: método nuevo del puerto `ChangeRepository`,
   `find_commit_with_reviews(project_id, head_sha)`, que devuelve el commit y las reviews de su run
   actual. Se llama solo para PRs, antes del `add`. Si las reviews terminan entre esa lectura y el
   alta, la decisión es conservadora (se revisa con normalidad), nunca incorrecta.
3. **Copia atómica**: `ChangeRepository.add(change, event, reused=())` recibe pares
   `(Review, ReviewReused)`. Dentro de la misma transacción del alta inserta cada review con
   `ON CONFLICT DO NOTHING` sobre `uq_reviews_natural_key` y, solo si la inserta, su evento. Si el
   change ya existía (`created=false`) no copia nada. La inserción de una fila de review se comparte
   con `SqlAlchemyReviewRepository` (función de módulo, sin duplicar el mapeo).
4. **Sin workflow**: `_ingest` no llama a `starter.start` cuando la PR nace reutilizada. Al
   reenviar la PR (`created=false`), pregunta `ChangeRepository.has_reused_reviews(change_id)` y,
   si el change sigue en el run 1 y tiene reviews reutilizadas, tampoco arranca. Con un `run` > 1
   (hubo reintento) se comporta como siempre, y el starter sigue siendo idempotente. Una carrera entre
   dos ingestas deja a la perdedora con `created=false`: ve las reviews del ganador (misma
   transacción) y no arranca nada.
5. **Marca de origen**: `reviews.reused_from_change_id` (UUID nullable, FK a `changes.id`, `ON DELETE
   SET NULL`), migración `g7d5e9b3c126` encadenada tras `f6c4d8a2b915`, con `downgrade`. Se
   expone como `reused_from` (UUID o `null`) en `ReviewResponse` y `ReviewBriefResponse`. El frontend
   no necesita el SHA del origen: es el mismo de la PR.
6. **Evento**: `review.reused` (`ReviewReused`: `review_id`, `change_id`, `project_id`, `agent`,
   `reused_from_change_id`), añadido a la lista blanca de eventos que expone la API. Un evento propio
   (y no `review.completed`) permite distinguir en la línea de tiempo y en las métricas lo que se
   revisó de lo que se copió.
7. **Respuesta de `POST /ingest/pr`**: campo aditivo `reused` (bool). `IngestResult.reused`.
   `ingest_pr` recibe los nombres de agente esperados desde `composition`.
8. **Estadísticas**: `agent_stats` cuenta todas las reviews, incluidas las copiadas. Es lo que ve el
   usuario en el canal y se acepta; separarlas sería otro change.

## Riesgos y límites

- Si el commit aún se está revisando cuando llega la PR, esta se revisa con normalidad (no espera).
- Si se borra el commit de origen, `ON DELETE SET NULL` pierde la marca y, al reenviar esa PR, se
  arrancaría su workflow; es un caso residual (borrar un change no tiene API hoy salvo quitar el
  proyecto, que borra todo).
- Una PR de varios commits nunca reutiliza (su diff es el de toda la rama).
- Los textos copiados ya fueron saneados al guardarse; no se reprocesan.
- Los ids de workflow, la guarda del starter y el flujo de reintento no cambian.
