# Tasks

## 1. Dominio

- [x] 1.1 `Review.reused_from_change_id` (opcional, por defecto `None`) y constructor `Review.reused_from(...)` que copia agente, resumen, nota, hallazgos y duración con `run` 1, estado `completed`, sin `raw_output` ni `error`
- [x] 1.2 Evento `ReviewReused` (`review.reused`) con su payload
- [x] 1.3 `domain/review_reuse.py::reviews_to_reuse`, función pura con tests unitarios de la decisión (mismo diff sí; diff distinto, SHA distinto, falta un agente, review fallida, run anterior y kind commit sobre commit no)

## 2. Aplicación

- [x] 2.1 Puerto `ChangeRepository`: `add(change, event, reused=())`, `find_commit_with_reviews` y `has_reused_reviews`; fakes de test al día
- [x] 2.2 `ingest_pr` recibe `agent_names`, decide la reutilización, no arranca el workflow cuando la PR nace o sigue reutilizada y devuelve `IngestResult.reused`; `composition` pasa `AGENT_NAMES`
- [x] 2.3 Lectura: la lista blanca de eventos expone `review.reused`; `ReviewBrief` lleva `reused_from`

## 3. Persistencia

- [x] 3.1 `ReviewModel.reused_from_change_id` (FK `ON DELETE SET NULL`) y migración `g7d5e9b3c126` con `downgrade`; test de migración arriba y abajo
- [x] 3.2 Inserción de una fila de review compartida entre repositorios; copia atómica en `SqlAlchemyChangeRepository.add`; `find_commit_with_reviews` y `has_reused_reviews`; `_briefs_for` con `reused_from`
- [x] 3.3 Tests de integración con Postgres real: copia atómica, idempotencia, carrera con ingestas concurrentes, `SET NULL` al borrar el commit

## 4. API

- [x] 4.1 `reused_from` en `ReviewResponse` y `ReviewBriefResponse`; `reused` en `IngestPrResponse`; `docs/openapi.json` regenerado
- [x] 4.2 Tests de API y del flujo e2e: commit revisado y PR con el mismo SHA y diff nace `completed` sin starter ni reviews nuevas; con diff distinto se revisa con normalidad

## 5. Frontend

- [x] 5.1 Tipos del cliente y mocks con `reusedFrom`; pill «Reutilizada del commit abc1234» en la review; sin orbe de agentes pendientes en estos changes; tests Vitest

## 6. Documentación y cierre

- [x] 6.1 `docs/architecture.md`, `docs/testing.md`, `README.md` y las frases de `docs/flujo-duelo.html` que dicen que commit y PR se revisan siempre por separado
- [ ] 6.2 `just ci` en verde, mutación en los módulos nuevos de dominio y aplicación, `openspec validate`
