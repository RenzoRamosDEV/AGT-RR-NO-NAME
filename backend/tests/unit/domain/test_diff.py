"""`summarize_diff`: archivos tocados y líneas añadidas/borradas de un `git diff`."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from duelo.domain.diff import (
    EMPTY_DIFF_SUMMARY,
    MAX_SUMMARY_FILES,
    FileDiff,
    summarize_diff,
)

TWO_FILES = """\
diff --git a/a.py b/a.py
index 111..222 100644
--- a/a.py
+++ b/a.py
@@ -1,3 +1,5 @@
 keep
-old
+new1
+new2
+new3
diff --git a/dir/b.py b/dir/b.py
new file mode 100644
--- /dev/null
+++ b/dir/b.py
@@ -0,0 +1,2 @@
+x
+y
"""


def test_counts_lines_per_file_and_in_total() -> None:
    summary = summarize_diff(TWO_FILES)

    assert summary.files_changed == 2
    assert (summary.additions, summary.deletions) == (5, 1)
    assert summary.files == (
        FileDiff(path="a.py", additions=3, deletions=1),
        FileDiff(path="dir/b.py", additions=2, deletions=0),
    )


def test_file_headers_are_not_counted_as_lines() -> None:
    # `---`/`+++` solo aparecen antes del primer hunk de cada archivo.
    summary = summarize_diff(TWO_FILES)

    assert summary.files[0].additions == 3 and summary.files[0].deletions == 1


def test_content_lines_starting_with_dashes_or_pluses_do_count_inside_a_hunk() -> None:
    diff = "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-- comentario sql\n+++x\n"

    summary = summarize_diff(diff)

    assert (summary.additions, summary.deletions) == (1, 1)


def test_context_and_no_newline_markers_are_ignored() -> None:
    diff = "diff --git a/x b/x\n@@ -1,2 +1,2 @@\n contexto\n-a\n+b\n\\ No newline at end of file\n"

    summary = summarize_diff(diff)

    assert (summary.additions, summary.deletions) == (1, 1)


def test_a_renamed_file_uses_the_destination_path() -> None:
    diff = "diff --git a/old name.py b/new name.py\nsimilarity index 90%\n@@ -1 +1 @@\n-a\n+b\n"

    assert summarize_diff(diff).files[0].path == "new name.py"


def test_a_path_that_itself_contains_the_destination_marker_uses_the_last_one() -> None:
    diff = "diff --git a/x b/y b/z b/w\n@@ -1 +1 @@\n-a\n+b\n"

    assert summarize_diff(diff).files[0].path == "w"


def test_a_header_without_destination_marker_keeps_the_rest_of_the_line() -> None:
    assert summarize_diff("diff --git rarisimo\n").files[0].path == "rarisimo"


@pytest.mark.parametrize("diff", ["", "no es un diff", "@@ -1 +1 @@\n+x\n", "+x\n-y\n"])
def test_text_without_a_git_file_header_has_no_files_and_no_lines(diff: str) -> None:
    assert summarize_diff(diff) == EMPTY_DIFF_SUMMARY


def test_file_without_hunks_still_counts_as_a_changed_file() -> None:
    summary = summarize_diff("diff --git a/x b/x\nBinary files a/x and b/x differ\n")

    assert summary.files_changed == 1 and (summary.additions, summary.deletions) == (0, 0)


@pytest.mark.parametrize(
    ("total", "listed"),
    [
        (MAX_SUMMARY_FILES - 1, MAX_SUMMARY_FILES - 1),
        (MAX_SUMMARY_FILES, MAX_SUMMARY_FILES),
        (MAX_SUMMARY_FILES + 1, MAX_SUMMARY_FILES),
        (MAX_SUMMARY_FILES + 50, MAX_SUMMARY_FILES),
    ],
)
def test_the_file_list_is_capped_but_the_count_and_totals_are_real(total: int, listed: int) -> None:
    diff = "".join(f"diff --git a/f{i} b/f{i}\n@@ -0,0 +1 @@\n+x\n" for i in range(total))

    summary = summarize_diff(diff)

    assert summary.files_changed == total
    assert summary.additions == total  # los totales cuentan también los archivos no listados
    assert len(summary.files) == listed
    assert summary.files[0].path == "f0"


def test_a_diff_cut_in_the_middle_of_a_hunk_is_summarized_as_received() -> None:
    summary = summarize_diff(TWO_FILES[: TWO_FILES.index("+new2") + 3])

    assert summary.files_changed == 1 and summary.files[0].additions == 2


@given(
    files=st.lists(
        st.tuples(st.integers(0, 6), st.integers(0, 6)),
        max_size=12,
    )
)
def test_totals_are_the_sum_of_the_listed_files(files: list[tuple[int, int]]) -> None:
    """Propiedad: con menos de 200 archivos, los totales son la suma de los archivos."""
    diff = ""
    for i, (adds, dels) in enumerate(files):
        diff += f"diff --git a/f{i} b/f{i}\n--- a/f{i}\n+++ b/f{i}\n@@ -1 +1 @@\n"
        diff += "".join(f"+a{n}\n" for n in range(adds)) + "".join(f"-d{n}\n" for n in range(dels))

    summary = summarize_diff(diff)

    assert [(f.additions, f.deletions) for f in summary.files] == files
    assert summary.additions == sum(a for a, _ in files)
    assert summary.deletions == sum(d for _, d in files)
    assert summary.files_changed == len(files)
