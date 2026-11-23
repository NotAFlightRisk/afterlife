import asyncio

from afterlife import crawl


class Tally:
    def __init__(self):
        self.saved = []

    def add(self, story, outcome):
        self.saved.append((story["id"], outcome["evidence"]))


def stories(count):
    return [
        {"id": i, "url": f"https://slow.example/{i}", "title": f"Story {i}", "before": None}
        for i in range(count)
    ]


def run_site(monkeypatch, outcome, count=8):
    async def fake_check(fetcher, github, story):
        return dict(outcome)

    monkeypatch.setattr(crawl, "check", fake_check)
    tally = Tally()
    asyncio.run(crawl.crawl_site(None, None, stories(count), tally))
    return tally.saved


def test_a_rate_limiting_host_leaves_the_rest_for_next_time(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "wall-429", "status": 429})
    assert [story for story, _ in saved] == [0, 1, 2, 3, 4]


def test_a_host_that_stops_answering_marks_the_rest_as_not_answering(monkeypatch):
    saved = run_site(monkeypatch, {"fate": "unsure", "evidence": "noanswer"})
    assert len(saved) == 8 and {evidence for _, evidence in saved} == {"noanswer"}


def test_one_good_answer_resets_the_count(monkeypatch):
    answers = iter(["noanswer"] * 4 + ["alive"] + ["noanswer"] * 4)

    async def fake_check(fetcher, github, story):
        return {"fate": "unsure", "evidence": next(answers)}

    monkeypatch.setattr(crawl, "check", fake_check)
    tally = Tally()
    asyncio.run(crawl.crawl_site(None, None, stories(9), tally))
    assert len(tally.saved) == 9
