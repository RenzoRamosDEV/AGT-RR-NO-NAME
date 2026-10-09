"""Guarda contra deriva: los límites del dominio deben ser los de las columnas reales."""

import pytest

from review_arena.adapters.persistence.models import ChangeModel, ReviewModel
from review_arena.domain import change, review


@pytest.mark.parametrize(
    ("model", "column", "limit"),
    [
        (ChangeModel, "head_sha", change.MAX_HEAD_SHA),
        (ChangeModel, "ref", change.MAX_REF),
        (ChangeModel, "url", change.MAX_URL),
        (ChangeModel, "title", change.MAX_TITLE),
        (ChangeModel, "author", change.MAX_AUTHOR),
        (ReviewModel, "agent", review.MAX_AGENT),
    ],
)
def test_domain_limit_equals_column_length(model, column: str, limit: int) -> None:
    assert model.__table__.c[column].type.length == limit
