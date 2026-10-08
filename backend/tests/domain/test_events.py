from uuid import uuid4

from review_arena.domain.events import ChangeCreated


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
