from __future__ import annotations

import pytest

from duelo.domain.project import MAX_SLUG, InvalidSlug, slug_for_repository


@pytest.mark.parametrize(
    "remote",
    [
        "https://github.com/acme/widgets",
        "https://github.com/acme/widgets.git",
        "https://github.com/acme/widgets/",
        "http://github.com/acme/widgets.git",
        "https://user:token@github.com/acme/widgets.git",
        "git@github.com:acme/widgets.git",
        "git@github.com:acme/widgets",
        "ssh://git@github.com/acme/widgets.git",
        "ssh://git@github.com:22/acme/widgets.git",
        "github.com:acme/widgets.git",
    ],
)
def test_a_github_remote_gives_owner_slash_repo(remote: str) -> None:
    assert slug_for_repository(remote, "carpeta") == ("acme/widgets", True)


@pytest.mark.parametrize(
    "remote",
    [
        None,
        "",
        "https://gitlab.com/acme/widgets.git",
        "git@bitbucket.org:acme/widgets.git",
        "https://github.com.evil.example/acme/widgets",
        "https://github.com/acme/widgets/tree/main",  # más de owner/repo
        "https://github.com/acme",  # sin repo
        "/srv/git/widgets.git",
    ],
)
def test_without_a_github_remote_the_folder_name_is_the_slug(remote: str | None) -> None:
    assert slug_for_repository(remote, "mi-repo") == ("mi-repo", False)


@pytest.mark.parametrize("owner", ["..", "."])
def test_a_github_remote_with_dot_segments_falls_back_to_the_folder(owner: str) -> None:
    assert slug_for_repository(f"git@github.com:{owner}/widgets.git", "carpeta") == (
        "carpeta",
        False,
    )


@pytest.mark.parametrize("folder", ["", ".", "..", "con espacio", "a/b", "ñandú", "x\x00y", "a;b"])
def test_an_invalid_folder_name_cannot_be_a_slug(folder: str) -> None:
    with pytest.raises(InvalidSlug, match="No se puede usar .* como nombre de proyecto") as caught:
        slug_for_repository(None, folder)

    assert repr(folder) in str(caught.value)


def test_the_slug_length_is_bounded_at_the_column_size() -> None:
    assert slug_for_repository(None, "a" * MAX_SLUG) == ("a" * MAX_SLUG, False)
    with pytest.raises(InvalidSlug, match=f"supera {MAX_SLUG} caracteres"):
        slug_for_repository(None, "a" * (MAX_SLUG + 1))
    with pytest.raises(InvalidSlug, match=f"supera {MAX_SLUG} caracteres"):
        slug_for_repository(f"git@github.com:{'o' * 200}/{'r' * 100}.git", "carpeta-ok")
