from __future__ import annotations

import os
import streamlit as st
from dotenv import load_dotenv

from reposcraper.github_loader import GitHubRepositoryLoader, RepositoryLoadError
from reposcraper.rag import RepositoryRAG
from reposcraper.llm import LLMError

load_dotenv()

st.set_page_config(
    page_title="RepoScraper · GitHub RAG",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

def get_secret(name: str, default: str = "") -> str:
    """Support Streamlit Community Cloud secrets and local environment variables."""
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

GROQ_KEY = get_secret("GROQ_API_KEY")
GROQ_MODEL = get_secret("GROQ_MODEL", "openai/gpt-oss-20b")
GITHUB_TOKEN = get_secret("GITHUB_TOKEN")

st.markdown("""
<style>
:root { color-scheme: dark; }
.block-container { max-width: 1220px; padding-top: 1.8rem; padding-bottom: 3rem; }
[data-testid="stAppViewContainer"] {
  background:
    radial-gradient(ellipse at 12% 0%, rgba(30, 110, 170, .17), transparent 38%),
    radial-gradient(ellipse at 92% 18%, rgba(103, 80, 190, .12), transparent 32%),
    #0b1018;
}
.hero {
  position: relative; overflow: hidden; padding: 2rem 2.1rem; border-radius: 22px;
  background: linear-gradient(115deg, rgba(17,39,65,.98), rgba(25,65,86,.94) 58%, rgba(45,47,95,.96));
  border: 1px solid rgba(127,185,225,.32); margin-bottom: 1.25rem;
  box-shadow: 0 18px 55px rgba(0,0,0,.20);
  animation: riseIn .65s ease-out both;
}
.hero:after {
  content:""; position:absolute; width:260px; height:260px; right:-75px; top:-135px;
  border:1px solid rgba(190,225,255,.16); border-radius:50%;
  box-shadow: 0 0 0 28px rgba(190,225,255,.035), 0 0 0 58px rgba(190,225,255,.025);
  animation: drift 9s ease-in-out infinite alternate;
}
.hero h1 { margin: 0; font-size: clamp(2rem, 4vw, 2.8rem); letter-spacing:-.04em; }
.hero p { margin:.65rem 0 0 0; color:#d4e5f5; max-width:740px; font-size:1.04rem; line-height:1.7; }
.eyebrow { text-transform:uppercase; letter-spacing:.17em; font-size:.72rem; font-weight:700; color:#8dd5ff; margin-bottom:.6rem; }
.section-card {
  border:1px solid rgba(137,161,190,.22); background:rgba(20,29,42,.70);
  border-radius:16px; padding:1rem 1.1rem; transition:transform .2s ease,border-color .2s ease;
}
.section-card:hover { transform:translateY(-2px); border-color:rgba(115,190,245,.45); }
div.stButton > button {
  border-radius:12px; min-height:2.7rem; font-weight:650;
  transition:transform .16s ease, box-shadow .16s ease, filter .16s ease;
}
div.stButton > button:hover { transform:translateY(-1px); box-shadow:0 8px 22px rgba(0,100,200,.18); filter:brightness(1.06); }
div[data-testid="stMetric"] {
  background:rgba(24,36,52,.7); border:1px solid rgba(137,161,190,.18);
  padding: .85rem 1rem; border-radius:14px;
}
[data-testid="stChatMessage"] { border:1px solid rgba(137,161,190,.14); border-radius:14px; padding:.7rem .85rem; }
.small-muted { color:#9aa9bb; font-size:.9rem; line-height:1.6; }
.cite-chip { display:inline-block; border:1px solid rgba(115,190,245,.22); border-radius:8px; padding:.15rem .45rem; background:rgba(24,68,92,.45); }
@keyframes riseIn { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:translateY(0); } }
@keyframes drift { from { transform:translate(0,0) rotate(0); } to { transform:translate(-20px,18px) rotate(12deg); } }
@media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation:none !important; transition:none !important; } }
</style>
<div class="hero">
  <div class="eyebrow">Grounded code intelligence</div>
  <h1>🔎 RepoScraper</h1>
  <p>Understand any public GitHub repository. Ask questions, explore implementation details, and get answers backed by the source code—not guesses.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ✦ About RepoScraper")
    st.markdown(
        "RepoScraper is a **GitHub RAG assistant**. Paste a public repository URL to index its readable source files, "
        "summarize the project, and ask questions with file-and-line references."
    )
    st.divider()
    st.markdown("### 🛡️ How grounding works")
    st.markdown(
        "1. **Fetch** selected source files from GitHub.\n"
        "2. **Chunk** code while preserving file paths and line numbers.\n"
        "3. **Retrieve** the most relevant chunks for your question.\n"
        "4. **Answer** using those excerpts and cite the evidence.\n\n"
        "If the retrieved code doesn't support an answer, RepoScraper should say **“Not found in the available repository evidence”** instead of inventing an answer."
    )
    st.divider()
    st.markdown("### 🚀 How to use")
    st.markdown(
        "1. Paste a public GitHub repository link.\n"
        "2. Click **Load repository**.\n"
        "3. Choose **Summarize repository** or ask a question.\n"
        "4. Open **Sources used** to verify the answer."
    )
    st.caption("Private repositories and execution of repository code are not supported.")

if "rag" not in st.session_state:
    st.session_state.rag = None
if "repo_info" not in st.session_state:
    st.session_state.repo_info = None
if "chat" not in st.session_state:
    st.session_state.chat = []
if "last_summary" not in st.session_state:
    st.session_state.last_summary = None
if "show_files" not in st.session_state:
    st.session_state.show_files = False

with st.container(border=True):
    st.markdown("### 🔗 Connect a repository")
    st.caption("Public repositories only · `.git` URLs are supported")
    repo_url = st.text_input(
        "Public GitHub repository URL",
        placeholder="https://github.com/owner/repository",
        label_visibility="collapsed",
    )
    col_a, col_b = st.columns([1, 1])
    with col_a:
        connect = st.button("📥  Load repository", type="primary", use_container_width=True)
    with col_b:
        clear = st.button("↻  Start fresh", use_container_width=True)

if clear:
    for key in ("rag", "repo_info", "chat", "last_summary"):
        st.session_state[key] = [] if key == "chat" else None
    st.session_state.show_files = False
    st.rerun()

if connect:
    if not GROQ_KEY:
        st.error("RepoScraper isn't configured with a Groq API key yet. The app owner must set GROQ_API_KEY in the deployment's Secrets settings.")
    elif not repo_url.strip():
        st.warning("Paste a GitHub repository URL to get started.")
    else:
        try:
            with st.spinner("Connecting to GitHub and collecting readable source files…"):
                repo = GitHubRepositoryLoader(token=GITHUB_TOKEN).load(repo_url)
            with st.spinner("Preparing the repository search index…"):
                rag = RepositoryRAG(repo, api_key=GROQ_KEY, model=GROQ_MODEL)
            st.session_state.rag = rag
            st.session_state.repo_info = repo
            st.session_state.chat = []
            st.session_state.last_summary = None
            st.session_state.show_files = False
            st.success(f"Connected to **{repo['full_name']}**.")
        except RepositoryLoadError as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Repository setup failed: {exc}")

if st.session_state.repo_info and st.session_state.rag:
    repo = st.session_state.repo_info
    rag = st.session_state.rag
    st.divider()
    st.markdown(f"## 📦 {repo['full_name']}")
    st.write(repo.get("description") or "This repository has no description in GitHub metadata.")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Files indexed", len(repo["files"]))
    m2.metric("Search chunks", len(rag.chunks))
    m3.metric("Main language", repo.get("language") or "Unknown")
    m4.metric("Stars", f"{repo.get('stargazers_count', 0):,}")
    st.markdown(f"[View repository on GitHub ↗]({repo['html_url']})")

    action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
    with action_col1:
        summarize = st.button("✨  Summarize repository", type="primary", use_container_width=True)
    with action_col2:
        show_files_btn = st.button("📂  Browse source files", use_container_width=True)
    with action_col3:
        st.markdown('<div class="small-muted">Answers use repository evidence only. Every answer can be checked against the cited source files.</div>', unsafe_allow_html=True)

    if show_files_btn:
        st.session_state.show_files = not st.session_state.show_files

    if summarize:
        with st.spinner("Reading key project files and preparing a grounded summary…"):
            try:
                answer = rag.summarize()
                if not answer.get("answer", "").strip():
                    answer = {
                        "answer": "Not enough evidence was retrieved to summarize this repository reliably. Try browsing the source files or asking about a specific module.",
                        "sources": answer.get("sources", []),
                    }
                st.session_state.last_summary = answer
            except Exception as exc:
                st.session_state.last_summary = {
                    "answer": f"The summary could not be generated. Details: {exc}",
                    "sources": [],
                }

    if st.session_state.last_summary:
        with st.container(border=True):
            st.markdown("### ✨ Project overview")
            st.markdown(st.session_state.last_summary["answer"])
            if st.session_state.last_summary.get("sources"):
                with st.expander("📚 Summary sources"):
                    for src in st.session_state.last_summary["sources"]:
                        st.markdown(f"- `{src['path']}` — lines {src['start_line']}–{src['end_line']}")

    if st.session_state.show_files:
        with st.expander("Repository source browser", expanded=True):
            paths = sorted(repo["files"].keys(), key=str.lower)
            selected = st.selectbox("Choose a file to inspect", paths)
            if selected:
                suffix = selected.rsplit(".", 1)[-1] if "." in selected else "text"
                st.code(repo["files"][selected], language=suffix if suffix in {
                    "py", "js", "jsx", "ts", "tsx", "json", "yaml", "yml", "toml",
                    "md", "html", "css", "sql", "sh", "java", "go", "rs"
                } else None)
                st.caption(f"Source path: `{selected}`")

    st.markdown("## 💬 Ask your repository")
    st.caption("Ask about a function, component, workflow, dependency, bug, or setup instruction.")
    for message in st.session_state.chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("📚 Sources used"):
                    for src in message["sources"]:
                        from urllib.parse import quote
                        path_url = quote(src["path"], safe="/")
                        url = f"{repo['html_url']}/blob/{repo['default_branch']}/{path_url}#L{src['start_line']}"
                        st.markdown(f"- [`{src['path']}`]({url}) — lines {src['start_line']}–{src['end_line']}")

    question = st.chat_input("Ask a question about this repository…")
    if question:
        st.session_state.chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching the source code and checking relevant evidence…"):
                try:
                    result = rag.ask(question)
                    answer_text = (result.get("answer") or "").strip()
                    if not answer_text:
                        answer_text = (
                            "🔎 **Not found in the available repository evidence.** "
                            "I couldn't produce a supported answer from the source excerpts retrieved. "
                            "Try naming a file, function, class, or feature."
                        )
                    st.markdown(answer_text)
                    if result.get("sources"):
                        with st.expander("📚 Sources used", expanded=True):
                            from urllib.parse import quote
                            for src in result["sources"]:
                                path_url = quote(src["path"], safe="/")
                                url = f"{repo['html_url']}/blob/{repo['default_branch']}/{path_url}#L{src['start_line']}"
                                st.markdown(f"- [`{src['path']}`]({url}) — lines {src['start_line']}–{src['end_line']}")
                    st.session_state.chat.append({
                        "role": "assistant",
                        "content": answer_text,
                        "sources": result.get("sources", []),
                    })
                except Exception as exc:
                    safe_message = (
                        "⚠️ **I couldn't complete that answer.** Please try again in a moment. "
                        "If this keeps happening, the app owner should check the server logs and API configuration."
                    )
                    st.error(safe_message)
                    st.session_state.chat.append({
                        "role": "assistant",
                        "content": safe_message,
                        "sources": [],
                    })

    if st.session_state.chat:
        transcript = "\n\n".join(
            f"## {item['role'].title()}\n\n{item['content']}" for item in st.session_state.chat
        )
        st.download_button(
            "⬇️  Download conversation as Markdown",
            transcript,
            file_name=f"{repo['name']}-repo-chat.md",
            mime="text/markdown",
        )
else:
    st.markdown("""
    <div class="section-card">
      <h3>Start exploring a codebase</h3>
      <p class="small-muted">Load a public GitHub repository to get a project summary, browse source files, and ask evidence-grounded questions.</p>
    </div>
    """, unsafe_allow_html=True)
