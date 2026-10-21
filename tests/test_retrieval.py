from reposcraper.chunking import chunk_repository
from reposcraper.retrieval import BM25Retriever


def test_retrieval_ranks_relevant_source():
    chunks = chunk_repository({
        "agents/judge.py": "def choose_verdict(arguments, critique):\n    return decide(arguments, critique)",
        "ui/app.py": "def render_homepage():\n    show_title()",
        "agents/critic.py": "def critique_arguments(pro, con):\n    compare_logic(pro, con)",
    })
    results = BM25Retriever(chunks).search("judge verdict arguments critique", top_k=2)
    assert results
    assert results[0][0].path == "agents/judge.py"


def test_empty_query_returns_no_results():
    chunks = chunk_repository({"x.py": "def hello(): pass"})
    assert BM25Retriever(chunks).search("!!!") == []
