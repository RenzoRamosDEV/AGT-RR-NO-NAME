"""Worker de desarrollo: una sola proceso para las task queues `platform` y `agents`, con
`FakeAgent`. El split real (platform en Docker, agents en local) llega con los agentes reales.

    uv run python -m duelo.worker
"""

from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from duelo.adapters.agents.fake import FakeAgent
from duelo.adapters.persistence.change_repository import SqlAlchemyChangeRepository
from duelo.adapters.persistence.db import create_engine, create_session_factory
from duelo.adapters.persistence.review_repository import SqlAlchemyReviewRepository
from duelo.config import WorkerSettings
from duelo.workflows.activities import ReviewActivities
from duelo.workflows.review_change import ReviewChangeWorkflow
from duelo.workflows.review_commit import ReviewCommitWorkflow


def build_workers(client: Client, settings: WorkerSettings) -> tuple[Worker, Worker]:
    engine = create_engine(settings.database_url)
    activities = ReviewActivities(
        session_factory=create_session_factory(engine),
        change_repository=SqlAlchemyChangeRepository,
        review_repository=SqlAlchemyReviewRepository,
        agents={name: FakeAgent(name) for name in settings.agent_names},
    )
    return (
        Worker(
            client,
            task_queue="platform",
            workflows=[ReviewChangeWorkflow, ReviewCommitWorkflow],
        ),
        Worker(client, task_queue="agents", activities=[activities.run_review]),
    )


async def main() -> None:
    settings = WorkerSettings()
    client = await Client.connect(settings.temporal_address)
    platform, agents = build_workers(client, settings)
    async with platform, agents:
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
