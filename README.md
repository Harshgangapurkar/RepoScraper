# RepoScraper — GitHub RAG Assistant

live link: https://reposcaper.streamlit.app

RepoScraper lets users paste a public GitHub repository URL, retrieve relevant source-code excerpts, and ask questions grounded in those excerpts. It can summarize the repository, show source files, cite file paths and line ranges, and optionally add external web-search results.

## Features

- Public GitHub repository loading with URL validation and API error handling.
- Bounded source-file selection that skips common generated directories and secret files.
- Line-aware code chunking with source path and line ranges.
- Dependency-free BM25 lexical retrieval.
- Groq-powered grounded question answering and project summaries.
- Repository citations and a source browser.
- Downloadable Markdown conversation.
- Tests for URL parsing, chunking, retrieval, and RAG citation metadata.

## Requirements

- Python 3.10 or newer
- Groq API key
- Internet access for GitHub, Groq, and optional web search

## Windows setup (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and set `GROQ_API_KEY` to your own key. Never commit `.env`.

If `python` is not recognized, install Python from python.org and ensure the installer adds Python to PATH. You can also use the Python executable already selected by Cursor.

## Run

```powershell
python -m streamlit run app.py
```

1. Enter a Groq API key in the sidebar or configure it in `.env`.
2. Paste a public repository URL such as `https://github.com/owner/repository`.
3. Click **Load repository**.
4. Click **Summarize repository** or ask a question.
5. Enable web search only when external context is useful.

## How it works

1. The GitHub loader validates the URL and fetches repository metadata/tree.
2. It fetches a bounded set of text/source files, avoiding secrets and generated folders.
3. The chunker splits files into overlapping line-aware chunks with source provenance.
4. BM25 ranks chunks relevant to the question.
5. Groq generates an answer from the retrieved excerpts, with instructions to cite file and line ranges and admit when evidence is missing.

## Important limitations

- Only public GitHub repositories are supported.
- Retrieval is lexical BM25, not embedding-based semantic search. Exact identifiers and technical terms work best.
- GitHub retrieval is bounded: up to 500 tree entries considered, 80 fetched files, 120 KB per file, and 1.5 MB total.
- The model can still make mistakes. Citations show retrieved evidence, but users should check the cited code.
- The app does not execute repository code.
- The GitHub token is optional and is only used to improve API rate limits.

## Tests

```powershell
python -m pytest -v
```

## Security

Do not commit API keys. Source files are treated as untrusted data; prompts instruct the model to ignore instructions found inside repository content. RepoScraper only reads selected public text files and never executes them.


## Deployment configuration

For Streamlit Community Cloud, add `GROQ_API_KEY` and `GROQ_MODEL` under **App settings → Secrets**. The application reads server-side Streamlit secrets or environment variables; users never enter or see the API key in the UI. Set `GITHUB_TOKEN` as a secret optionally to increase GitHub API rate limits.
