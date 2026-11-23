import pytest

from afterlife.classify import Seen, classify, slug_match, wants_probe, wants_then

STORY = "https://example.com/2016/05/13/giving-up-on-julia.html"
TITLE = "Giving up on Julia"


def fate(seen: Seen, url: str = STORY, title: str = TITLE, before: str = "") -> tuple[str, str]:
    return classify(url, title, seen, before)


@pytest.mark.parametrize("status", [404, 410])
def test_a_plain_404_or_410_is_dead(status):
    assert fate(Seen(STORY, status)) == ("dead", str(status))


def test_a_domain_that_no_longer_resolves_is_dead():
    assert fate(Seen(STORY, error="dns")) == ("dead", "dns")


@pytest.mark.parametrize("error", ["timeout", "refused", "conn", "dns-temp"])
def test_no_answer_waits_for_its_second_try(error):
    assert fate(Seen(STORY, error=error)) == ("unsure", "noanswer")
    assert fate(Seen(STORY, error=error), before="noanswer") == ("dead", "noanswer-twice")


def test_a_tls_failure_is_never_a_death():
    assert fate(Seen(STORY, error="tls"), before="noanswer") == ("unsure", "tls")


@pytest.mark.parametrize("error", ["reset", "stall"])
def test_a_host_that_resets_or_stalls_everything_is_a_wall_not_a_death(error):
    assert fate(Seen(STORY, error=error), before="noanswer") == ("unsure", error)


@pytest.mark.parametrize("status", [401, 402, 403, 429, 451])
def test_walls_are_unsure(status):
    assert fate(Seen(STORY, status)) == ("unsure", f"wall-{status}")


@pytest.mark.parametrize("status", [400, 406, 500, 503])
def test_odd_statuses_are_unsure_never_dead(status):
    assert fate(Seen(STORY, status)) == ("unsure", f"status-{status}")


def test_a_challenge_page_is_unsure():
    seen = Seen(STORY, 200, html=True, title="Just a moment...")
    assert fate(seen) == ("unsure", "challenge")


def test_a_story_about_captchas_is_not_a_challenge_page():
    url, title = "https://example.com/why-captcha-is-broken", "Why CAPTCHA is broken"
    seen = Seen(url, 200, html=True, title="Why CAPTCHA is broken | Example")
    assert fate(seen, url, title) == ("alive", "alive")


def test_a_consent_redirect_is_unsure():
    url = "https://news.yahoo.com/some-story-123.html"
    seen = Seen("https://consent.yahoo.com/v2/collectConsent?sessionId=1", 200, 1, True, "Yahoo")
    assert fate(seen, url, "Some story") == ("unsure", "consent")


def test_a_parked_domain_lands_elsewhere():
    seen = Seen(STORY, 200, html=True, title="example.com", parked=True)
    assert fate(seen) == ("elsewhere", "parked")


def test_same_url_is_alive():
    seen = Seen("http://www.example.com/2016/05/13/giving-up-on-julia.html", 200, 1, True, "Hi")
    assert fate(seen) == ("alive", "alive")


def test_a_query_string_that_names_the_page_still_counts():
    url = "https://example.com/article.php?id=5"
    seen = Seen("https://example.com/article.php", 200, 1, True, "Example news")
    assert fate(seen, url, "A story") == ("elsewhere", "unrelated")


def test_tracking_junk_doesnt_count_as_a_move():
    seen = Seen(STORY + "?utm_source=hn", 200, html=True, title="Something")
    assert fate(seen) == ("alive", "alive")


def test_a_redirect_whose_title_matches_has_moved():
    seen = Seen(
        "https://vitaut.net/posts/2016/giving-up-on-julia/", 200, 1, True, "Giving up on Julia"
    )
    assert fate(seen) == ("moved", "moved")


def test_the_site_name_alone_isnt_a_title_match():
    url = "https://blog.docker.com/2016/02/docker-1-10/"
    seen = Seen("https://www.docker.com/blog/", 200, 1, True, "Docker Blog")
    assert fate(seen, url, "Docker 1.10") == ("elsewhere", "home")


def test_a_redirect_to_the_home_page_lands_elsewhere():
    seen = Seen("https://example.com/", 200, 1, True, "Example")
    assert fate(seen) == ("elsewhere", "home")


def test_a_redirect_to_some_other_page_lands_elsewhere():
    seen = Seen("https://example.com/travel-tips", 200, 1, True, "Travel tips")
    assert fate(seen) == ("elsewhere", "unrelated")


def test_twitter_to_x_is_a_move():
    post = "/jack/status/1984576043164270938"
    assert slug_match("https://twitter.com" + post, "https://x.com" + post, "A post")


def test_a_soft_404_is_unsure():
    url = "https://example.com/some/old/page"
    seen = Seen(url, 200, html=True, title="Example", probe=(200, "Example"))
    assert wants_probe(url, "A story about something", seen)
    assert fate(seen, url, "A story about something") == ("unsure", "soft404")


def test_a_probe_that_404s_means_the_page_is_real():
    url = "https://example.com/some/old/page"
    seen = Seen(url, 200, html=True, title="Example", probe=(404, "Not found"))
    assert fate(seen, url, "A story about something") == ("alive", "alive")


def test_a_home_page_that_changed_title_gets_the_wayback_check():
    url = "https://straight2spam.xyz/"
    seen = Seen(url, 200, html=True, title="A pollinator garden")
    assert wants_then(url, "Show HN: Straight2Spam", seen)
    assert not wants_then(url, "Show HN: A pollinator garden", seen)


def test_a_redirect_to_a_tag_page_is_not_a_move():
    url, title = "https://example.com/2014/postgres-tricks", "Postgres tricks"
    seen = Seen("https://example.com/tag/postgres/", 200, 1, True, "Postgres | Example")
    assert fate(seen, url, title) == ("elsewhere", "home")


@pytest.mark.parametrize("junk", ["?guccounter=1", ";jsessionid=ABC123"])
def test_a_session_or_consent_bit_on_the_same_page_is_alive(junk):
    seen = Seen(STORY + junk, 200, 1, True, "Something else entirely")
    assert fate(seen) == ("alive", "alive")


def test_a_sign_in_page_is_unsure():
    url = "https://docs.google.com/document/d/abc/edit"
    seen = Seen("https://accounts.google.com/v3/signin/identifier", 200, 2, True, "Sign in")
    assert fate(seen, url, "A design doc") == ("unsure", "login")


def test_a_page_that_says_not_found_is_a_soft_404():
    seen = Seen(STORY, 200, html=True, title="Page not found | Example")
    assert fate(seen) == ("unsure", "soft404")


def test_a_404_that_bounces_to_the_home_page_is_dead():
    seen = Seen("https://example.com/", 200, 1, True, "Example", gone=404)
    assert fate(seen) == ("dead", "404")


def test_a_404_that_bounces_to_the_story_has_moved():
    seen = Seen("https://vitaut.net/posts/2016/giving-up-on-julia/", 200, 1, True, TITLE, gone=404)
    assert fate(seen) == ("moved", "moved")


def test_dropping_the_html_extension_is_a_move_not_a_parent_folder():
    url = "http://blog.asmartbear.com/consulting-company-accounting.html"
    title = "The unfortunate math behind consulting companies"
    seen = Seen(
        "https://longform.asmartbear.com/consulting-company-accounting/", 200, 1, True, title
    )
    assert fate(seen, url, title) == ("moved", "moved")


def test_a_redirect_up_a_folder_lands_elsewhere():
    url = "https://example.com/blog/2014/05/some-post"
    seen = Seen("https://example.com/blog/2014/", 200, 1, True, "Some post archive")
    assert fate(seen, url, "Some post") == ("elsewhere", "home")


@pytest.mark.parametrize(
    "url,final",
    [
        (
            "http://www.npr.org/blogs/money/2010/10/04/130329523/how-fake",
            "https://www.npr.org/sections/money/2010/10/04/130329523/how-fake",
        ),
        (
            "http://articles.latimes.com/2010/may/16/opinion/la-oe-0516-how-fake",
            "https://www.latimes.com/archives/la-xpm-2010-may-16-la-oe-0516-how-fake-story.html",
        ),
    ],
)
def test_articles_that_live_under_sections_or_archives_have_moved(url, final):
    seen = Seen(final, 200, 1, True, "How fake money got real - NPR")
    assert fate(seen, url, "How fake money got real") == ("moved", "moved")


def test_two_blank_titles_arent_a_soft_404():
    url = "https://6octaves.blogspot.com/2017/06/interview.html"
    seen = Seen(url, 200, html=True, title="", probe=(200, ""))
    assert fate(seen, url, "Interview with a demoscener") == ("alive", "alive")
