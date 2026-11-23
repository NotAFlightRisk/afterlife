"""Sorts what the crawler saw into one of five fates, plus the evidence for it.

Only plain deaths are dead: the domain's gone, a 404 or 410, or no answer twice a week apart.
Everything odder is "elsewhere" (it goes somewhere that isn't the story) or "unsure".
"""

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from .urls import host_of, is_root, norm, page_of, pairs_of, query_of, site

ALIVE, MOVED, DEAD, ELSEWHERE, UNSURE = "alive", "moved", "dead", "elsewhere", "unsure"
NO_ANSWER = {"refused", "timeout", "conn", "dns-temp"}
WALLS = {401, 402, 403, 429, 451, 999}
LISTING = re.compile(
    r"/(tags?|categor(y|ies)|topics?|archives?|search|sections?|labels?)(/|$)", re.I
)
LOGIN = re.compile(r"/(sign-?in|log-?in|authwall|servicelogin|session/new|users/sign_in)\b", re.I)
NOT_FOUND = re.compile(
    r"\b(404|not found|no longer (available|exists)|(does not|doesn't) exist|page missing)\b", re.I
)

STOP = set(
    "the a an and or of to in on for with from by at is are was be how why what your you our we"
    " it its this that my i not new using use show hn ask into about vs via".split()
)
SITE_WORDS = {"blog", "news", "home", "page", "com", "org", "net", "www", "github", "medium"}
PARKING = (
    "sedoparking",
    "sedo.com",
    "bodis.com",
    "parkingcrew",
    "afternic",
    "hugedomains",
    "dan.com/",
    "this domain is for sale",
    "this domain may be for sale",
    "buy this domain",
    "domain is for sale",
    "parklogic",
    "domainmarket",
    "undeveloped.com",
    "dropcatch",
    "parked domain name",
    "domain-for-sale",
    "atom.com/name",
)
WALL_TITLES = (
    "just a moment",
    "attention required",
    "cf-chl",
    "captcha",
    "are you a robot",
    "access denied",
    "verify you are human",
    "please enable js",
    "enable javascript and cookies",
    "unusual traffic",
    "pardon our interruption",
    "request blocked",
    "bot detection",
    "not a bot",
    "one moment, please",
    "checking your browser",
    "suspicious",
    "too-generic user-agent",
    "accès restreint",
    "access restricted",
    "client challenge",
)


@dataclass(frozen=True)
class Seen:
    """What one fetch of a story's URL came back with."""

    url: str
    status: int = 0
    hops: int = 0
    html: bool = False
    title: str = ""
    parked: bool = False
    error: str = ""
    probe: tuple[int, str] | None = None
    gone: int = 0


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in STOP}


def overlap(a: str, b: str, hosts: str = "") -> bool:
    """Do two titles share enough words, once the site's own name is out of the way?"""
    drop = tokens(hosts.replace(".", " ")) | SITE_WORDS
    left, right = tokens(a) - drop, tokens(b) - drop
    if not left or not right:
        return False
    shared = len(left & right)
    return shared >= 2 or shared / min(len(left), len(right)) >= 0.34


def last_segment(url: str) -> str:
    return urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1].lower()


def slug(url: str) -> set[str]:
    words = last_segment(url).rsplit(".", 1)[0].replace("-", " ").replace("_", " ")
    return tokens(words)


def slug_match(url: str, final: str, hn_title: str) -> bool:
    if query_of(url) and query_of(url) != query_of(final):
        return False
    before, after = slug(url), slug(final)
    if before and before == after:
        return True
    old, new = last_segment(url), last_segment(final)
    same_folder = (
        urlsplit(url).path.lower().rsplit("/", 1)[0]
        == (urlsplit(final).path.lower().rsplit("/", 1)[0])
    )
    if min(len(old), len(new)) > 3 and (new.startswith(old) or old.startswith(new)) and same_folder:
        return True
    told = tokens(hn_title)
    return (
        bool(after) and len(after & told) >= 1 and len(after & (told | before)) / len(after) >= 0.5
    )


def is_listing(url: str, final: str) -> bool:
    """A home page, a section or tag index, or a parent folder of where the story used to be."""
    old, new = urlsplit(url).path.rstrip("/"), urlsplit(final).path.rstrip("/")
    parent = bool(new) and old.startswith(new + "/")
    section = new.lower() in ("/blog", "/news", "/articles", "/posts") or LISTING.search(new)
    return is_root(final) or parent or bool(section)


def is_parked(text: str) -> bool:
    low = text[:60_000].lower()
    return any(marker in low for marker in PARKING)


def same_page(url: str, seen: Seen) -> bool:
    """Same page, even if the site tacked a session or consent bit onto the query."""
    if norm(seen.url) == norm(url):
        return True
    return page_of(seen.url) == page_of(url) and pairs_of(url) <= pairs_of(seen.url)


def is_login(url: str, seen: Seen) -> bool:
    if same_page(url, seen):
        return False
    host = host_of(seen.url)
    return host.startswith(("accounts.", "login.", "auth.", "signin.", "sso.")) or bool(
        LOGIN.search(urlsplit(seen.url).path)
    )


def is_consent(url: str, seen: Seen) -> bool:
    if same_page(url, seen):
        return False
    final = seen.url.lower()
    cross = site(host_of(url)) != site(host_of(seen.url))
    return (
        host_of(final).startswith("consent.")
        or "collectconsent" in final
        or "/consent" in urlsplit(final).path
        or ("consent" in seen.title.lower() and cross)
    )


def is_challenge(url: str, hn_title: str, seen: Seen) -> bool:
    path = urlsplit(seen.url).path.lower()
    sent_off = not same_page(url, seen) and (
        "anubis" in seen.url.lower() or re.search(r"challenge|captcha|cspace-bad", path)
    )
    walled = any(w in seen.title.lower() for w in WALL_TITLES)
    return bool(sent_off) or (walled and not overlap(hn_title, seen.title))


def wants_probe(url: str, hn_title: str, seen: Seen) -> bool:
    """Worth asking for a made-up path, in case this host serves the same page for anything."""
    return (
        200 <= seen.status < 300
        and seen.html
        and same_page(url, seen)
        and not is_root(url)
        and not overlap(hn_title, seen.title, host_of(url))
    )


def wants_then(url: str, hn_title: str, seen: Seen) -> bool:
    """A home page that doesn't look like the story any more, for the Wayback title check."""
    return same_page(url, seen) and is_root(url) and not overlap(hn_title, seen.title, host_of(url))


def classify(url: str, hn_title: str, seen: Seen, before: str = "") -> tuple[str, str]:
    """(fate, evidence) for one story. `before` is the evidence from its previous check."""
    if seen.error == "dns":
        return DEAD, "dns"
    if seen.error in NO_ANSWER:
        return (DEAD, "noanswer-twice") if before == "noanswer" else (UNSURE, "noanswer")
    if seen.error:
        return UNSURE, seen.error
    status, title = seen.status, seen.title
    hosts = host_of(url) + " " + host_of(seen.url)
    if is_consent(url, seen):
        return UNSURE, "consent"
    if status in WALLS:
        return UNSURE, f"wall-{status}"
    if is_challenge(url, hn_title, seen):
        return UNSURE, "challenge"
    if is_login(url, seen):
        return UNSURE, "login"
    if seen.parked and not overlap(hn_title, title, hosts):
        return ELSEWHERE, "parked"
    if status in (404, 410):
        return DEAD, str(status)
    if not 200 <= status < 300:
        return UNSURE, f"status-{status}"
    if NOT_FOUND.search(title) and not overlap(hn_title, title):
        return (DEAD, str(seen.gone)) if seen.gone else (UNSURE, "soft404")
    if same_page(url, seen):
        if seen.probe == (200, title) and wants_probe(url, hn_title, seen):
            return UNSURE, "soft404"
        return ALIVE, "alive"
    listing = is_listing(url, seen.url)
    if not listing and (overlap(hn_title, title, hosts) or slug_match(url, seen.url, hn_title)):
        return MOVED, "moved"
    if seen.gone:
        return DEAD, str(seen.gone)
    return ELSEWHERE, "home" if listing else "unrelated"
