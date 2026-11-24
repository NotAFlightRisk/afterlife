import gzip

import pytest

from afterlife import build
from afterlife.db import connect, save_check, save_stories

STORY = {
    "id": 1,
    "url": "https://example.com/a",
    "title": "A story",
    "points": 120,
    "comments": 4,
    "posted": 1262390400,
    "show_hn": 0,
}


@pytest.fixture
def db(tmp_path):
    db = connect(tmp_path / "afterlife.db")
    save_stories(db, [STORY, {**STORY, "id": 2, "url": None, "title": "Ask HN: hello?"}])
    return db


def check(db, at, fate, evidence):
    save_check(db, 1, at, {"fate": fate, "evidence": evidence})


def test_an_unsure_recheck_keeps_the_verdict_before_it(db):
    check(db, 100, "alive", "alive")
    check(db, 200, "unsure", "wall-403")
    assert build.verdicts(db)[0]["fate"] == "alive"


def test_a_later_decisive_check_wins(db):
    check(db, 100, "unsure", "noanswer")
    check(db, 200, "dead", "noanswer-twice")
    check(db, 300, "unsure", "wall-429")
    assert build.verdicts(db)[0]["evidence"] == "noanswer-twice"


def test_never_decided_shows_unsure(db):
    check(db, 100, "unsure", "noanswer")
    assert build.verdicts(db)[0]["fate"] == "unsure"


def test_a_walled_dot_carries_its_last_good_capture(db):
    check(db, 100, "unsure", "wall-403")
    db.execute("insert into captures values (1, 150, 'good', '20200101000000', 404, null)")
    assert build.dot(build.verdicts(db)[0])[-1] == 404


@pytest.mark.parametrize("evidence", ["dns", "noanswer-twice"])
def test_a_gone_domain_and_a_dead_server_read_the_same(db, evidence):
    check(db, 100, "dead", evidence)
    assert build.card(build.verdicts(db)[0])["evidence"] == "gone"


def test_a_repurposed_home_page_shows_what_it_was(db):
    detail = {"then": True, "captured": "20100105000000", "was": "A story, then"}
    save_check(db, 1, 100, {"fate": "unsure", "evidence": "home-changed", "detail": detail})
    shown = build.card(build.verdicts(db)[0])
    assert (shown["was"], shown["then"]) == ("A story, then", "20100105000000")
    assert "detail" not in shown


def test_the_build_writes_every_kind_of_file(db, tmp_path):
    check(db, 100, "dead", "404")
    out = tmp_path / "data"
    build.run(db, out)
    assert (out / "grid/2010.json").exists() and (out / "day/2010-01-02.json").exists()
    assert (out / f"id/{build.shard(1)}.json").exists()
    assert (out / f"host/{build.shard('example.com')}.json").exists()
    rows = gzip.decompress((out / "afterlife.csv.gz").read_bytes()).decode().splitlines()
    assert rows == ["hn_id,url,fate,checked", "1,https://example.com/a,dead,1970-01-01"]
