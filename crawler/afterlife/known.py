"""Sites with an API that answers better than their pages do: GitHub, YouTube and X."""

import json
import re
import time
from urllib.parse import urlencode

import aiohttp

from .classify import ALIVE, DEAD, MOVED, UNSURE
from .net import TIMEOUT, UA, Fetcher, Gate, NoAnswer, kind_of, retry_after

GITHUB = re.compile(
    r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/(issues|pull)/(\d+))?/?(?:[?#].*)?$",
    re.I,
)
YOUTUBE = re.compile(
    r"https?://(?:(?:www|m)\.)?(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|v/)|youtu\.be/)"
    r"([\w-]{11})",
    re.I,
)
TWEET = re.compile(
    r"https?://(?:(?:www|mobile)\.)?(twitter|x)\.com/(\w+)/status(?:es)?/(\d+)", re.I
)


async def get_json(fetcher: Fetcher, gate: Gate, url: str, headers: dict | None = None):
    """(status, json or None, response headers), politely through `gate`."""
    try:
        async with (
            gate,
            fetcher.session.get(
                url, headers={"User-Agent": UA, **(headers or {})}, timeout=TIMEOUT
            ) as r,
        ):
            body = await r.read() if r.status == 200 else b""
            return r.status, json.loads(body) if body else None, r.headers
    except (TimeoutError, aiohttp.ClientError, OSError, ValueError) as e:
        raise NoAnswer(kind_of(e)) from e


class GitHub:
    """Repos and issues through the REST API. The token's 5,000 an hour is shared with whatever
    else uses it, so this takes under half and steps aside when under 30% is left."""

    def __init__(self, fetcher: Fetcher, token: str):
        self.fetcher, self.gate = fetcher, Gate(1.5)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def call(self, path: str):
        while True:
            status, data, headers = await get_json(
                self.fetcher, self.gate, "https://api.github.com" + path, self.headers
            )
            remaining = int(headers.get("x-ratelimit-remaining", 1))
            if remaining < int(headers.get("x-ratelimit-limit", 0)) * 0.3:
                self.gate.hold(max(int(headers.get("x-ratelimit-reset", 0)) - time.time(), 0) + 5)
            limited = status in (403, 429) and (remaining == 0 or "retry-after" in headers)
            if not limited:
                return status, data
            self.gate.hold(retry_after(headers.get("retry-after")))

    async def check(self, url: str, match: re.Match) -> dict | None:
        """None when only the page itself can settle it (a 404 might be /blog/something)."""
        owner, repo, kind, number = match.groups()
        path = f"/repos/{owner}/{repo}" + (f"/issues/{number}" if number else "")
        status, data = await self.call(path)
        if status == 200:
            now = data["html_url"]
            was = f"https://github.com/{owner}/{repo}" + (f"/{kind}/{number}" if number else "")
            moved = now.lower().replace("/pull/", "/issues/") != was.lower().replace(
                "/pull/", "/issues/"
            )
            detail = {"via": "github", "archived": data.get("archived", False) or None}
            return {
                "fate": MOVED if moved else ALIVE,
                "evidence": "moved" if moved else "alive",
                "status": 200,
                "final": now,
                "title": data.get("full_name") or data.get("title"),
                "detail": {k: v for k, v in detail.items() if v},
            }
        if status == 410:
            return {"fate": DEAD, "evidence": "410", "status": 410, "detail": {"via": "github"}}
        if status == 404:
            return None
        return {
            "fate": UNSURE,
            "evidence": f"status-{status}",
            "status": status,
            "detail": {"via": "github"},
        }


async def oembed(
    fetcher: Fetcher, endpoint: str, target: str, moved_to: str = "", gone=(404,)
) -> dict | None:
    """A video or post through its oEmbed endpoint. None if the endpoint won't say."""
    gate = fetcher.gate(endpoint.split("/")[2])
    query = urlencode({"format": "json", "url": target})
    status, data, _ = await get_json(fetcher, gate, f"{endpoint}?{query}")
    detail = {"via": "oembed"}
    if status == 200:
        fate = MOVED if moved_to else ALIVE
        return {
            "fate": fate,
            "evidence": fate,
            "status": 200,
            "final": moved_to or target,
            "title": (data or {}).get("title") or (data or {}).get("author_name"),
            "detail": detail,
        }
    if status in gone:
        return {"fate": DEAD, "evidence": "404", "status": status, "detail": detail}
    if status in (401, 403):
        return {"fate": UNSURE, "evidence": "private", "status": status, "detail": detail}
    return None


async def check(fetcher: Fetcher, github: GitHub | None, url: str) -> dict | None:
    if github and (match := GITHUB.match(url)):
        return await github.check(url, match)
    if match := YOUTUBE.match(url):
        video = f"https://www.youtube.com/watch?v={match.group(1)}"
        return await oembed(fetcher, "https://www.youtube.com/oembed", video, gone=(400, 404))
    if match := TWEET.match(url):
        brand, user, post = match.groups()
        on_x = f"https://x.com/{user}/status/{post}"
        moved_to = on_x if brand.lower() == "twitter" else ""
        return await oembed(fetcher, "https://publish.twitter.com/oembed", on_x, moved_to)
    return None


def lane(url: str, github: bool) -> str | None:
    """Which gate an API-settled story queues behind, if it is one."""
    if github and GITHUB.match(url):
        return "api.github.com"
    if YOUTUBE.match(url):
        return "youtube.com"
    if TWEET.match(url):
        return "twitter.com"
    return None
