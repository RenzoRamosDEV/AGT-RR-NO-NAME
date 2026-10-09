"""Resumen de un diff en formato `git diff`: archivos tocados y líneas añadidas/borradas."""

from __future__ import annotations

from dataclasses import dataclass, replace

# Cota de `files`: el recuento real va en `files_changed`; la lista no debe inflar la fila.
MAX_SUMMARY_FILES = 200

_FILE_HEADER = "diff --git "
_DEST_MARKER = " b/"
_HUNK_HEADER = "@@"


@dataclass(frozen=True, slots=True)
class FileDiff:
    path: str
    additions: int
    deletions: int


@dataclass(frozen=True, slots=True)
class DiffSummary:
    files_changed: int
    additions: int
    deletions: int
    files: tuple[FileDiff, ...]


EMPTY_DIFF_SUMMARY = DiffSummary(files_changed=0, additions=0, deletions=0, files=())


def _destination_path(header: str) -> str:
    rest = header.removeprefix(_FILE_HEADER)
    return rest.rsplit(_DEST_MARKER, 1)[1] if _DEST_MARKER in rest else rest


def summarize_diff(diff: str) -> DiffSummary:
    """Cuenta por archivo las líneas `+`/`-` de los hunks.

    `diff --git` abre un archivo y sale del hunk, así que las cabeceras `---`/`+++` no cuentan;
    dentro de un hunk, una línea de contenido que empiece por `++` o `--` sí. Solo entiende el
    formato de `git diff`; en otro formato el resumen queda vacío o parcial.
    """
    files: list[FileDiff] = []
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith(_FILE_HEADER):
            files.append(FileDiff(path=_destination_path(line), additions=0, deletions=0))
            in_hunk = False
        elif line.startswith(_HUNK_HEADER):
            in_hunk = True
        elif in_hunk and files:
            current = files[-1]
            if line.startswith("+"):
                files[-1] = replace(current, additions=current.additions + 1)
            elif line.startswith("-"):
                files[-1] = replace(current, deletions=current.deletions + 1)
    return DiffSummary(
        files_changed=len(files),
        additions=sum(f.additions for f in files),
        deletions=sum(f.deletions for f in files),
        files=tuple(files[:MAX_SUMMARY_FILES]),
    )
