import pytest
from reposcraper.github_loader import parse_github_url, RepositoryLoadError


@pytest.mark.parametrize("url,expected", [
    ("https://github.com/openai/openai-python", ("openai", "openai-python")),
    ("https://github.com/owner/repo.git", ("owner", "repo")),
    ("https://www.github.com/a/b/", ("a", "b")),
])
def test_parse_github_url(url, expected):
    assert parse_github_url(url) == expected


@pytest.mark.parametrize("url", [
    "", "https://gitlab.com/a/b", "https://github.com/a", "https://github.com/a/b/issues",
    "javascript:alert(1)",
])
def test_reject_invalid_github_urls(url):
    with pytest.raises(RepositoryLoadError):
        parse_github_url(url)
