import re
from urllib.parse import parse_qsl, urlencode, urlsplit

SECOND_LEVEL = {"co", "com", "org", "ac", "gov", "net", "ne", "edu"}
TRACKING = re.compile(r"^(utm_\w+|ref|source|fbclid|gclid|mc_\w+)$")
ROOTISH = re.compile(r"/(index\.\w+|home|en|en-us|[a-z]{2}(-[a-z]{2})?)/?")


def host_of(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def site(host: str) -> str:
    """Near enough the registrable domain, so foo.blogspot.com and bar.blogspot.com share a gate."""
    parts = host.lower().split(".")
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def pairs_of(url: str) -> set[tuple[str, str]]:
    pairs = parse_qsl(urlsplit(url).query, keep_blank_values=True)
    return {(k, v) for k, v in pairs if not TRACKING.match(k)}


def query_of(url: str) -> str:
    return urlencode(sorted(pairs_of(url)))


def page_of(url: str) -> str:
    """Host and path, minus www, trailing slashes, index pages and ;jsessionid-style bits."""
    path = urlsplit(url).path.split(";", 1)[0]
    return host_of(url) + re.sub(r"/(index\.(html?|php))?$", "", path).lower()


def norm(url: str) -> str:
    """Scheme, www, trailing slashes, index pages and tracking junk don't make a URL different."""
    query = query_of(url)
    return page_of(url) + ("?" + query if query else "")


def is_root(url: str) -> bool:
    path = urlsplit(url).path
    bare = path in ("", "/") or ROOTISH.fullmatch(path.lower()) is not None
    return bare and not query_of(url)


def origin(url: str) -> str:
    s = urlsplit(url)
    return f"{s.scheme}://{s.netloc}"
