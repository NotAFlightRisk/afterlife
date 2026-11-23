import asyncio

import pytest

from afterlife import known
from afterlife.net import MAX_WAIT, Gate


class Fetcher:
    def gate(self, host):
        return Gate(0)


def answer(monkeypatch, *statuses):
    replies = iter(statuses)

    async def fake_get_json(fetcher, gate, url, headers=None):
        status = next(replies)
        return status, {"title": "A video"} if status == 200 else None, {"retry-after": "0"}

    monkeypatch.setattr(known, "get_json", fake_get_json)
    monkeypatch.setattr(known, "retry_after", lambda value: 0)
    video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    return asyncio.run(known.oembed(Fetcher(), "https://www.youtube.com/oembed", video))


@pytest.mark.parametrize(
    "status,fate,evidence",
    [
        (200, "alive", "alive"),
        (404, "dead", "404"),
        (400, "unsure", "status-400"),
        (401, "unsure", "private"),
        (500, "unsure", "status-500"),
    ],
)
def test_oembed_answers_map_to_fates(monkeypatch, status, fate, evidence):
    outcome = answer(monkeypatch, status)
    assert (outcome["fate"], outcome["evidence"]) == (fate, evidence)


def test_oembed_waits_out_a_rate_limit(monkeypatch):
    assert answer(monkeypatch, 429, 429, 200)["fate"] == "alive"


def test_oembed_never_guesses_after_three_rate_limits(monkeypatch):
    assert answer(monkeypatch, 429, 429, 429)["evidence"] == "wall-429"


def test_a_tweet_on_twitter_dot_com_has_moved_to_x(monkeypatch):
    replies = iter([200])

    async def fake_get_json(fetcher, gate, url, headers=None):
        return next(replies), {"author_name": "jack"}, {}

    monkeypatch.setattr(known, "get_json", fake_get_json)
    outcome = asyncio.run(known.check(Fetcher(), None, "https://twitter.com/jack/status/20"))
    assert (outcome["fate"], outcome["final"]) == ("moved", "https://x.com/jack/status/20")


def test_oembed_leaves_a_site_alone_that_asked_for_a_long_rest(monkeypatch):
    class Busy:
        def gate(self, host):
            gate = Gate(0)
            gate.hold(MAX_WAIT + 60)
            return gate

    async def never(*args, **kwargs):
        raise AssertionError("asked anyway")

    monkeypatch.setattr(known, "get_json", never)
    video = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    outcome = asyncio.run(known.oembed(Busy(), "https://www.youtube.com/oembed", video))
    assert outcome["evidence"] == "wall-429"
