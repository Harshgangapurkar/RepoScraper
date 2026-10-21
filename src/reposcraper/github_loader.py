from __future__ import annotations

import re
import requests
from typing import Any

API_ROOT = "https://api.github.com"
MAX_TREE_ITEMS = 500
MAX_SOURCE_FILES = 80
MAX_FILE_BYTES = 120_000
MAX_TOTAL_BYTES = 1_500_000

SKIP_DIRS = {
    ".git", ".github", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".next", "coverage", "vendor", "target",
}
SKIP_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials.json", "secrets.json",
}
SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".php", ".rb", ".swift", ".scala",
    ".sql", ".sh", ".ps1", ".html", ".css", ".scss", ".json", ".yaml",
    ".yml", ".toml", ".ini", ".md", ".rst", ".txt", ".xml", ".dockerfile",
}
IMPORTANT_NAMES = {
    "readme", "requirements.txt", "pyproject.toml", "package.json",
    "cargo.toml", "go.mod", "pom.xml", "build.gradle", "dockerfile",
    "makefile", "environment.yml", "environment.yaml",
}


class RepositoryLoadError(RuntimeError):
    """Friendly, user-actionable repository loading error."""


def parse_github_url(url: str) -> tuple[str, str]:
    cleaned = (url or "").strip().rstrip("/")
    cleaned = re.sub(r"\.git$", "", cleaned, flags=re.IGNORECASE)
    match = re.fullmatch(r"https?://(?:www\.)?github\.com/([^/]+)/([^/?#]+)", cleaned, re.IGNORECASE)
    if not match:
        raise RepositoryLoadError("Enter a repository URL like https://github.com/owner/repository.")
    owner, name = match.group(1), match.group(2)
    if owner in {".", ".."} or name in {".", ".."}:
        raise RepositoryLoadError("Invalid GitHub repository URL.")
    return owner, name


class GitHubRepositoryLoader:
    def __init__(self, token: str = "", timeout: int = 20):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "RepoScraper/1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise RepositoryLoadError(f"Could not reach GitHub: {exc}") from exc
        if response.status_code == 404:
            raise RepositoryLoadError("Repository not found or not public. Check the owner, name, and visibility.")
        if response.status_code == 403:
            raise RepositoryLoadError("GitHub API rate limit or access restriction. Add GITHUB_TOKEN to .env and retry.")
        if response.status_code >= 400:
            raise RepositoryLoadError(f"GitHub API returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise RepositoryLoadError("GitHub returned an unexpected response.") from exc

    def load(self, url: str) -> dict[str, Any]:
        owner, name = parse_github_url(url)
        metadata = self._get_json(f"{API_ROOT}/repos/{owner}/{name}")
        branch = metadata.get("default_branch") or "main"
        tree = self._get_json(f"{API_ROOT}/repos/{owner}/{name}/git/trees/{branch}?recursive=1")
        tree_items = tree.get("tree", [])
        if not isinstance(tree_items, list):
            raise RepositoryLoadError("GitHub returned an invalid repository tree.")

        chosen = []
        for item in tree_items[:MAX_TREE_ITEMS]:
            if item.get("type") != "blob":
                continue
            path = str(item.get("path", ""))
            parts = path.replace("\\", "/").split("/")
            lower = path.lower()
            if not path or any(part.lower() in SKIP_DIRS for part in parts):
                continue
            if parts[-1].lower() in SKIP_NAMES or parts[-1].lower().startswith(".env"):
                continue
            suffix = "." + parts[-1].rsplit(".", 1)[-1].lower() if "." in parts[-1] else ""
            base = parts[-1].lower()
            if suffix in SOURCE_SUFFIXES or base in IMPORTANT_NAMES or base == "dockerfile":
                chosen.append((path, item.get("size", 0)))
        chosen.sort(key=lambda x: (0 if x[0].lower().endswith(("readme.md", "pyproject.toml", "requirements.txt", "package.json")) else 1, x[0].count("/"), x[0].lower()))

        files: dict[str, str] = {}
        total_bytes = 0
        for path, declared_size in chosen:
            if len(files) >= MAX_SOURCE_FILES or total_bytes >= MAX_TOTAL_BYTES:
                break
            if declared_size and declared_size > MAX_FILE_BYTES:
                continue
            content = self._fetch_raw(owner, name, branch, path)
            if content is None:
                continue
            encoded_len = len(content.encode("utf-8", errors="ignore"))
            if encoded_len > MAX_FILE_BYTES or total_bytes + encoded_len > MAX_TOTAL_BYTES:
                continue
            files[path] = content
            total_bytes += encoded_len

        if not files:
            raise RepositoryLoadError("No readable source files were found in this repository.")
        return {
            "name": metadata.get("name", name),
            "full_name": metadata.get("full_name", f"{owner}/{name}"),
            "html_url": metadata.get("html_url", f"https://github.com/{owner}/{name}"),
            "description": metadata.get("description") or "",
            "language": metadata.get("language") or "",
            "stargazers_count": metadata.get("stargazers_count", 0),
            "default_branch": branch,
            "files": files,
            "tree_count": len(tree_items),
            "truncated": bool(tree.get("truncated")) or len(tree_items) > MAX_TREE_ITEMS,
            "files_fetched": len(files),
            "bytes_fetched": total_bytes,
        }

    def _fetch_raw(self, owner: str, name: str, branch: str, path: str) -> str | None:
        # Download only bounded, selected text files from the repository's default branch.
        from urllib.parse import quote
        url = f"https://raw.githubusercontent.com/{quote(owner)}/{quote(name)}/{quote(branch, safe='')}/{quote(path, safe='/')}"
        try:
            response = self.session.get(url, timeout=self.timeout)
        except requests.RequestException:
            return None
        if response.status_code != 200:
            return None
        content_type = response.headers.get("content-type", "")
        if "text" not in content_type and "json" not in content_type and "octet-stream" not in content_type:
            return None
        try:
            text = response.content.decode("utf-8")
        except UnicodeDecodeError:
            return None
        # Avoid accidentally treating binary content as source text.
        if "\x00" in text:
            return None
        return text
