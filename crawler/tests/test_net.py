import asyncio
import errno

import pytest

from afterlife.net import (
    AGENT,
    PublicResolver,
    decode,
    is_public,
    kind_of,
    made_up,
    next_hop,
    robots_rules,
    title_of,
)
from afterlife.urls import is_root, norm, site

URL = "https://zverovich.net/2016/05/13/giving-up-on-julia.html"


def test_a_location_header_is_followed_relative_to_the_page():
    assert next_hop(URL, 301, "/new", "") == "https://zverovich.net/new"


def test_a_404_pages_javascript_swap_is_followed():
    swap = 'window.location.href.replace("zverovich.net", "vitaut.net")'
    page = f"<script>window.location.href = {swap}</script>"
    assert next_hop(URL, 404, None, page) == URL.replace("zverovich.net", "vitaut.net")


def test_a_big_404_page_with_a_swap_in_it_is_left_alone():
    page = 'window.location = window.location.href.replace("a", "b")' + " " * 5000
    assert next_hop(URL, 404, None, page) is None


def test_a_meta_refresh_is_followed():
    page = '<meta http-equiv="refresh" content="0; url=\'https://example.com/moved\'">'
    assert next_hop(URL, 200, None, page) == "https://example.com/moved"


def test_a_meta_refresh_to_itself_goes_nowhere():
    page = f'<meta http-equiv="refresh" content="300; url={URL}">'
    assert next_hop(URL, 200, None, page) is None


def test_titles_come_out_unescaped_and_tidy():
    assert title_of("<title>\n  Tom &amp; Jerry\n</title>") == "Tom & Jerry"


def test_a_bad_charset_falls_back_to_utf8():
    assert decode("café".encode(), "not-a-charset") == "café"


def test_norm_ignores_scheme_www_slashes_and_tracking():
    assert norm("http://www.Example.com/a/?utm_source=hn") == norm("https://example.com/a")
    assert norm("https://example.com/a?id=1") != norm("https://example.com/a?id=2")


def test_root_means_no_path_and_no_query():
    assert is_root("https://example.com/")
    assert is_root("https://example.com/en/")
    assert not is_root("https://example.com/?p=123")


def test_subdomains_of_a_platform_share_a_site():
    assert site("foo.blogspot.com") == site("bar.blogspot.com") == "blogspot.com"
    assert site("news.bbc.co.uk") == "bbc.co.uk"


class FakeResolver:
    def __init__(self, *hosts):
        self.hosts = hosts

    async def resolve(self, host, port=0, family=0):
        return [{"host": ip, "port": port} for ip in self.hosts]

    async def close(self):
        pass


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "192.168.0.1", "169.254.169.254", "::1"])
def test_private_addresses_are_refused(ip):
    resolver = PublicResolver(FakeResolver(ip))
    with pytest.raises(OSError) as refused:
        asyncio.run(resolver.resolve("sneaky.example"))
    assert kind_of(refused.value) == "private"


def test_only_the_public_addresses_get_through():
    resolver = PublicResolver(FakeResolver("10.0.0.1", "93.184.215.14"))
    found = asyncio.run(resolver.resolve("example.com"))
    assert [f["host"] for f in found] == ["93.184.215.14"]


def test_connection_failures_boil_down_to_kinds():
    assert kind_of(ConnectionRefusedError(errno.ECONNREFUSED, "no")) == "refused"
    assert kind_of(ConnectionResetError(errno.ECONNRESET, "rst")) == "reset"
    assert kind_of(TimeoutError()) == "timeout"


def test_a_slow_refresh_is_a_reload_not_a_redirect():
    page = '<meta http-equiv="refresh" content="1800; url=/">'
    assert next_hop(URL, 200, None, page) is None


def test_a_refresh_for_browsers_without_javascript_is_ignored():
    page = '<noscript><meta http-equiv="refresh" content="0; url=/nojs"></noscript>'
    assert next_hop(URL, 200, None, page) is None


def test_the_probe_asks_for_a_sibling_that_cant_exist():
    assert made_up("https://example.com/news/article.php?id=12345").startswith(
        "https://example.com/news/article.php?id=hn-afterlife-"
    )
    assert made_up("https://example.com/posts/my-post").startswith(
        "https://example.com/posts/hn-afterlife-"
    )


@pytest.mark.parametrize(
    "ip",
    ["::127.0.0.1", "::ffff:0:127.0.0.1", "64:ff9b::7f00:1", "::ffff:10.0.0.1", "2002:7f00:1::"],
)
def test_private_ipv4_wrapped_in_ipv6_is_refused(ip):
    assert not is_public(ip)


def test_a_real_ipv6_address_is_public():
    assert is_public("2606:4700:4700::1111")


def test_a_robots_group_for_another_bot_with_a_similar_name_isnt_ours():
    rules = robots_rules("User-agent: LinkCheck\nDisallow: /\n\nUser-agent: *\nDisallow: /search\n")
    assert rules.can_fetch(AGENT, "https://www.theatlantic.com/technology/archive/2013/01/x/1/")
    assert not rules.can_fetch(AGENT, "https://www.theatlantic.com/search?q=x")


def test_a_robots_group_that_names_us_is_obeyed():
    rules = robots_rules("User-agent: hn-afterlife-linkcheck\nDisallow: /\nCrawl-delay: 5\n")
    assert not rules.can_fetch(AGENT, "https://example.com/anything")
    assert rules.crawl_delay(AGENT) == 5


def test_a_site_that_shuts_out_every_unnamed_bot_shuts_us_out():
    assert not robots_rules("User-agent: *\nDisallow: /\n").can_fetch(AGENT, "https://x.com/a")
