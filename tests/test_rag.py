from reposcraper.rag import RepositoryRAG


class FakeAnswerer:
    def generate(self, system_prompt, user_prompt, temperature=0.2):
        assert "Retrieved repository source excerpts" in user_prompt or "Source excerpts" in user_prompt
        return "The verdict is selected by the judge [agents/judge.py:L1-L2]."


def test_ask_retrieves_and_cites_source_metadata():
    repo = {
        "full_name": "demo/argus",
        "files": {
            "agents/judge.py": "def choose_verdict(arguments, critique):\n    return 'FOR'",
            "README.md": "A debate system with advocate, opposition, critic, and judge agents.",
        },
    }
    rag = RepositoryRAG.__new__(RepositoryRAG)
    rag.repo = repo
    from reposcraper.chunking import chunk_repository
    from reposcraper.retrieval import BM25Retriever
    rag.chunks = chunk_repository(repo["files"])
    rag.retriever = BM25Retriever(rag.chunks)
    rag.answerer = FakeAnswerer()
    result = rag.ask("How does the judge choose a verdict?")
    assert "judge" in result["answer"].lower()
    assert result["sources"]
    assert result["sources"][0]["path"] in {"agents/judge.py", "README.md"}


class EmptyAnswerer:
    def generate(self, system_prompt, user_prompt, temperature=0.2):
        return "   "


def test_empty_llm_answer_returns_explicit_not_found_message():
    repo = {
        "full_name": "demo/argus",
        "files": {"agents/judge.py": "def choose_verdict(arguments, critique):\n    return 'FOR'"},
    }
    rag = RepositoryRAG.__new__(RepositoryRAG)
    rag.repo = repo
    from reposcraper.chunking import chunk_repository
    from reposcraper.retrieval import BM25Retriever
    rag.chunks = chunk_repository(repo["files"])
    rag.retriever = BM25Retriever(rag.chunks)
    rag.answerer = EmptyAnswerer()
    result = rag.ask("How does the judge choose a verdict?")
    assert result["answer"]
    assert "not found" in result["answer"].lower()
