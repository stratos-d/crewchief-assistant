"""Check GitHub for a newer release. Only the public releases API is contacted; nothing about the user is sent."""
import re

RELEASES_API = "https://api.github.com/repos/stratos-d/crewchief-assistant/releases/latest"
RELEASES_PAGE = "https://github.com/stratos-d/crewchief-assistant/releases/latest"


def parse_version(tag):
    """'v0.7.1' -> (0, 7, 1); anything else (such as 'dev') -> None."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (tag or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def newer_release(current):
    """The latest release tag if it is newer than `current`, otherwise None. Never raises."""
    mine = parse_version(current)
    if mine is None:
        return None  # development build
    try:
        import httpx
        response = httpx.get(RELEASES_API, timeout=5, headers={"Accept": "application/vnd.github+json"})
        latest = response.json().get("tag_name", "")
    except Exception:
        return None
    theirs = parse_version(latest)
    return latest if theirs and theirs > mine else None
