import httpx
import pytest

from src.updates import newer_release, parse_version


def fake_latest(monkeypatch, tag=None, error=None):
    def get(url, **kwargs):
        if error:
            raise error
        return type("Response", (), {"json": lambda self: {"tag_name": tag}})()
    monkeypatch.setattr(httpx, "get", get)


@pytest.mark.parametrize("tag, expected", [("v0.7.1", (0, 7, 1)), ("1.2.3", (1, 2, 3)), ("dev", None), ("", None)])
def test_parse_version(tag, expected):
    assert parse_version(tag) == expected


@pytest.mark.parametrize("current, latest, expected", [
    ("v0.7.1", "v0.8.0", "v0.8.0"),
    ("v0.7.1", "v0.7.1", None),
    ("v0.8.0", "v0.7.1", None),
    ("v0.7.9", "v0.7.10", "v0.7.10"),  # numeric, not alphabetical
])
def test_newer_release(monkeypatch, current, latest, expected):
    fake_latest(monkeypatch, tag=latest)
    assert newer_release(current) == expected


def test_development_builds_never_check(monkeypatch):
    fake_latest(monkeypatch, error=AssertionError("should not be called"))
    assert newer_release("dev") is None


def test_network_errors_are_silent(monkeypatch):
    fake_latest(monkeypatch, error=httpx.ConnectError("offline"))
    assert newer_release("v0.7.1") is None
