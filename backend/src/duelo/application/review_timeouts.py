"""Plazos y reintentos de una review, en un solo sitio: el workflow y la configuración no se
desincronizan."""

from __future__ import annotations

from datetime import timedelta

# Plazo de la activity `run_review` (`start_to_close_timeout` del workflow).
RUN_REVIEW_START_TO_CLOSE = timedelta(minutes=5)

# Lo que debe sobrar entre el plazo del agente y el de la activity: al vencer el CLI hay que
# matar su grupo de procesos, esperar la recolección acotada de su salida, borrar los temporales y
# persistir la `Review(failed)`.
AGENT_TIMEOUT_MARGIN = timedelta(seconds=30)

# Máximo de `AGENT_TIMEOUT_SECONDS`.
MAX_AGENT_TIMEOUT_SECONDS = (RUN_REVIEW_START_TO_CLOSE - AGENT_TIMEOUT_MARGIN).total_seconds()

# Reintentos de `run_review` y de su compensación (la `RetryPolicy` se construye en el workflow,
# `application/` no depende de Temporal). Tres intentos en total con backoff exponencial, nunca
# más de un minuto entre dos: un fallo de infraestructura se nota en minutos, no en horas.
RUN_REVIEW_RETRY_MAX_ATTEMPTS = 3
RUN_REVIEW_RETRY_INITIAL = timedelta(seconds=1)
RUN_REVIEW_RETRY_BACKOFF = 2.0
RUN_REVIEW_RETRY_MAX_INTERVAL = timedelta(minutes=1)
