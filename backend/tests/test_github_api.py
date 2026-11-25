from __future__ import annotations

from student_workbench.adapters.github_api import parse_github_remote


def test_parses_https_remote():
    assert parse_github_remote("https://github.com/owner/repo.git") == (
        "owner",
        "repo",
    )


def test_parses_https_remote_without_git_suffix():
    assert parse_github_remote("https://github.com/owner/repo") == ("owner", "repo")


def test_parses_ssh_remote():
    assert parse_github_remote("git@github.com:owner/repo.git") == ("owner", "repo")


def test_ignores_non_github_remotes():
    assert parse_github_remote("https://gitlab.com/owner/repo.git") is None
    assert parse_github_remote("git@gitlab.com:owner/repo.git") is None
    assert parse_github_remote("") is None
    assert parse_github_remote(None) is None