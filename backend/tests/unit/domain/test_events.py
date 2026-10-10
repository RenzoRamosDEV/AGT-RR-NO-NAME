from uuid import uuid4

from duelo.domain.events import (
    ChangeCreated,
    CommitDiscarded,
    CommitRestored,
    CommitReverted,
    ReviewCompleted,
    ReviewFailed,
)


def test_change_created_payload_keeps_all_fields() -> None:
    change_id = uuid4()
    project_id = uuid4()
    event = ChangeCreated(
        change_id=change_id,
        project_id=project_id,
        kind="commit",
        head_sha="a" * 40,
    )

    payload = event.to_payload()

    assert event.type == "change.created"
    assert payload == {
        "change_id": str(change_id),
        "project_id": str(project_id),
        "kind": "commit",
        "head_sha": "a" * 40,
    }


def test_review_completed_payload_keeps_all_fields() -> None:
    review_id, change_id, project_id = uuid4(), uuid4(), uuid4()
    event = ReviewCompleted(
        review_id=review_id, change_id=change_id, project_id=project_id, agent="agent_1"
    )

    assert event.type == "review.completed"
    assert event.to_payload() == {
        "review_id": str(review_id),
        "change_id": str(change_id),
        "project_id": str(project_id),
        "agent": "agent_1",
    }


def test_review_failed_payload_keeps_all_fields() -> None:
    review_id, change_id, project_id = uuid4(), uuid4(), uuid4()
    event = ReviewFailed(
        review_id=review_id,
        change_id=change_id,
        project_id=project_id,
        agent="agent_2",
        error="timeout",
    )

    assert event.type == "review.failed"
    assert event.to_payload() == {
        "review_id": str(review_id),
        "change_id": str(change_id),
        "project_id": str(project_id),
        "agent": "agent_2",
        "error": "timeout",
    }


def test_commit_discarded_payload_keeps_all_fields() -> None:
    change_id, project_id = uuid4(), uuid4()
    event = CommitDiscarded(change_id=change_id, project_id=project_id)

    assert event.type == "commit.discarded"
    assert event.to_payload() == {"change_id": str(change_id), "project_id": str(project_id)}


def test_commit_restored_payload_keeps_all_fields() -> None:
    change_id, project_id = uuid4(), uuid4()
    event = CommitRestored(change_id=change_id, project_id=project_id)

    assert event.type == "commit.restored"
    assert event.to_payload() == {"change_id": str(change_id), "project_id": str(project_id)}


def test_commit_reverted_payload_names_the_commit_that_reverts_it() -> None:
    change_id, project_id, reverter_id = uuid4(), uuid4(), uuid4()
    event = CommitReverted(
        change_id=change_id, project_id=project_id, reverted_by_change_id=reverter_id
    )

    assert event.type == "commit.reverted"
    assert event.to_payload() == {
        "change_id": str(change_id),
        "project_id": str(project_id),
        "reverted_by_change_id": str(reverter_id),
    }
