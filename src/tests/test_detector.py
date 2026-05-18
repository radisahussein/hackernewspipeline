"""Tests for keyword detection — explicit false positive cases required."""
import pytest

from transforms.detector import detect_keywords


# --- Rust ---

def test_detect_rust_in_plain_title():
    assert "Rust" in detect_keywords("Rust is memory safe")


def test_detect_rust_false_positive_rusty():
    assert "Rust" not in detect_keywords("Getting rusty at piano")


def test_detect_rust_false_positive_rusty_pipes():
    assert "Rust" not in detect_keywords("rusty old pipes in my basement")


def test_detect_rust_in_url_path():
    assert "Rust" in detect_keywords("New compiler released", "https://github.com/rust-lang/rust")


# --- Go ---

def test_detect_go_in_plain_title():
    assert "Go" in detect_keywords("Go 1.22 released with new features")


def test_detect_go_not_matched_in_going():
    assert "Go" not in detect_keywords("Going to use a new approach")


def test_detect_go_not_matched_go_to():
    assert "Go" not in detect_keywords("We need to go to the store")


def test_detect_go_not_matched_go_ahead():
    assert "Go" not in detect_keywords("Go ahead and submit your PR")


def test_detect_go_not_matched_go_back():
    assert "Go" not in detect_keywords("Go back and read the docs first")


# --- Next.js ---

def test_detect_nextjs_in_title():
    assert "Next.js" in detect_keywords("Next.js 14 released with server actions")


def test_detect_nextjs_not_matched_next():
    # "Next" alone should not match "Next.js"
    result = detect_keywords("The next version is coming soon")
    assert "Next.js" not in result


# --- Python ---

def test_detect_python_in_title():
    assert "Python" in detect_keywords("Python 3.12 performance improvements")


def test_detect_python_in_url():
    assert "Python" in detect_keywords("Type hints guide", "https://docs.python.org/3/")


# --- TypeScript ---

def test_detect_typescript_in_title():
    assert "TypeScript" in detect_keywords("TypeScript 5.4 adds new infer features")


# --- Docker ---

def test_detect_docker_in_title():
    assert "Docker" in detect_keywords("Docker Desktop 4.26 released")


# --- URL domain extraction ---

def test_detect_keyword_from_github_url_path():
    assert "Rust" in detect_keywords("Show HN", "https://github.com/rust-lang/cargo")


def test_detect_astro_from_url():
    assert "Astro" in detect_keywords("New framework released", "https://astro.build/blog/astro-4")


# --- Multiple keywords ---

def test_detect_multiple_keywords_in_one_title():
    result = detect_keywords("Building a FastAPI backend with Docker and PostgreSQL")
    assert "FastAPI" in result
    assert "Docker" in result


def test_detect_returns_deduplicated_list():
    # Same keyword mentioned twice in title
    result = detect_keywords("Rust and Rust toolchain updates in Rust 2024")
    assert result.count("Rust") == 1


# --- Edge cases ---

def test_detect_empty_title_returns_empty():
    assert detect_keywords("") == []


def test_detect_none_url_handled_gracefully():
    result = detect_keywords("Python tips and tricks", None)
    assert "Python" in result


def test_detect_unrelated_title_returns_empty():
    result = detect_keywords("My cat learned to open doors today")
    assert result == []
