from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CodeChunk:
    chunk_id: str
    path: str
    start_line: int
    end_line: int
    text: str


def chunk_repository(files: dict[str, str], max_chars: int = 1800, overlap_lines: int = 5) -> list[CodeChunk]:
    """Split source files into line-aware chunks and preserve path/line provenance."""
    chunks: list[CodeChunk] = []
    for path, content in files.items():
        lines = content.splitlines()
        if not lines:
            continue
        start = 0
        while start < len(lines):
            end = start
            size = 0
            while end < len(lines) and size + len(lines[end]) + 1 <= max_chars:
                size += len(lines[end]) + 1
                end += 1
            if end == start:  # One unusually long line.
                end = start + 1
            text = "\n".join(lines[start:end])
            chunks.append(CodeChunk(
                chunk_id=f"{path}:{start + 1}-{end}",
                path=path,
                start_line=start + 1,
                end_line=end,
                text=text,
            ))
            if end >= len(lines):
                break
            start = max(start + 1, end - overlap_lines)
    return chunks
