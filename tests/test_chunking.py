from reposcraper.chunking import chunk_repository


def test_chunks_keep_path_and_line_numbers():
    source = "\n".join(f"line_{i}" for i in range(1, 31))
    chunks = chunk_repository({"src/example.py": source}, max_chars=40, overlap_lines=2)
    assert len(chunks) > 1
    assert all(c.path == "src/example.py" for c in chunks)
    assert chunks[0].start_line == 1
    assert chunks[0].end_line >= chunks[0].start_line
    assert chunks[-1].end_line == 30


def test_empty_files_are_ignored():
    assert chunk_repository({"empty.py": ""}) == []
