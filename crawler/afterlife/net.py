"""A polite fetcher. One request at a time per site, a second apart, robots.txt obeyed, never more
than 400 KB of a page, and no private or reserved address on any hop."""

import asyncio
import errno
import html
import ipaddress
import re
import socket
import ssl
import time
import zlib
from collections import defaultdict
from email.utils import parsedate_to_datetime
from typing import NamedTuple
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import aiohttp
from aiohttp.abc import AbstractResolver
from yarl import URL

from .classify import Seen, is_parked
from .urls import norm, site

AGENT = "hn-afterlife-linkcheck"
UA = f"{AGENT}/1.0 (+https://afterlife.peng.ly/about; hackerafterlife@peng.ly)"
HEADERS = {"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en"}
TIMEOUT = aiohttp.ClientTimeout(total=45, connect=10, sock_read=20)
MAX_BODY, MAX_ROBOTS, MAX_HOPS, MAX_DELAY, MAX_WAIT = 400_000, 500_000, 10, 120, 300
REDIRECTS = {301, 302, 303, 307, 308}
GONE_DNS = {socket.EAI_NONAME, getattr(socket, "EAI_NODATA", -5)}
SETTLED = {"dns", "private", "badurl"}
MAX_REFRESH = 10
WRAPPERS = [
    ipaddress.ip_network(net)
    for net in ("::/96", "::ffff:0:0:0/96", "64:ff9b::/96", "64:ff9b:1::/48")
]

META_REFRESH = re.compile(
    r"""<meta[^>]+http-equiv=["']?refresh["']?[^>]+content=["']?\s*(\d+)\s*;\s*url=['"]?([^"'>\s]+)""",
    re.I,
)
NOSCRIPT = re.compile(r"<noscript.*?</noscript>", re.S | re.I)
JS_SWAP = re.compile(
    r"""window\.location(?:\.href)?\s*=\s*window\.location\.href\.replace\(\s*['"]([^'"]+)['"]"""
    r"""\s*,\s*['"]([^'"]+)['"]"""
)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.I)
COOKIE_NAME = re.compile(r"[\w!#$%&'*+.^`|~:-]+", re.ASCII)


class Reply(NamedTuple):
    status: int
    location: str | None
    html: bool
    text: str
    cookies: dict


class NoAnswer(Exception):
    def __init__(self, kind: str):
        super().__init__(kind)
        self.kind = kind


def is_public(ip: str) -> bool:
    """Global, and not an IPv6 wrapper round a private IPv4 (mapped, NAT64, 6to4, Teredo)."""
    address = ipaddress.ip_address(ip.split("%")[0])
    if address.version == 6:
        inner = address.ipv4_mapped or address.sixtofour or (address.teredo or (None, None))[1]
        if inner is None and any(address in net for net in WRAPPERS):
            inner = ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
        if inner is not None and not inner.is_global:
            return False
    return address.is_global


def legacy_tls() -> ssl.SSLContext:
    """What an old browser would still talk to: no verification, old TLS, old renegotiation."""
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
    context.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
    context.options |= ssl.OP_LEGACY_SERVER_CONNECT
    context.set_ciphers("DEFAULT:@SECLEVEL=0")
    return context


class PublicResolver(AbstractResolver):
    """Hands aiohttp only public addresses, so a redirect can't walk us onto the local network."""

    def __init__(self, inner: AbstractResolver | None = None):
        self.inner = inner or aiohttp.ThreadedResolver()

    async def resolve(self, host, port=0, family=socket.AF_INET):
        found = [r for r in await self.inner.resolve(host, port, family) if is_public(r["host"])]
        if not found:
            raise OSError(errno.EACCES, f"{host} only resolves to private addresses")
        return found

    async def close(self):
        await self.inner.close()


def kind_of(exc: BaseException) -> str:
    """Boil a connection failure down to the few kinds the classifier cares about. A stall is
    a server that took the connection and then never answered, which is how some walls look."""
    if isinstance(exc, aiohttp.SocketTimeoutError):
        return "stall"
    if isinstance(exc, asyncio.TimeoutError | aiohttp.ServerTimeoutError):
        return "timeout"
    if isinstance(exc, aiohttp.ServerDisconnectedError):
        return "reset"
    if isinstance(exc, aiohttp.ClientSSLError):
        return "tls"
    if isinstance(exc, aiohttp.ClientResponseError):
        return "badreply"
    if isinstance(exc, aiohttp.InvalidURL | ValueError):
        return "badurl"
    os_error = getattr(exc, "os_error", None) or (exc if isinstance(exc, OSError) else None)
    code = getattr(os_error, "errno", None)
    if code == errno.EACCES:
        return "private"
    if code == errno.ECONNREFUSED:
        return "refused"
    if code in (errno.ECONNRESET, errno.EPIPE, errno.ECONNABORTED):
        return "reset"
    return "conn"


def title_of(text: str) -> str:
    found = TITLE.search(text)
    return re.sub(r"\s+", " ", html.unescape(found.group(1))).strip()[:200] if found else ""


def decode(raw: bytes, charset: str | None) -> str:
    sniffed = CHARSET.search(raw[:4096])
    for name in (charset, sniffed and sniffed.group(1).decode("ascii", "ignore"), "utf-8"):
        if name:
            try:
                return raw.decode(name, "replace")
            except LookupError:
                continue
    return raw.decode("utf-8", "replace")


def next_hop(url: str, status: int, location: str | None, text: str) -> str | None:
    """Where this response sends us: a Location, a meta refresh, or a 404 page's JS swap."""
    if status in REDIRECTS and location:
        return urljoin(url, location.strip())
    head = NOSCRIPT.sub("", text[:5000])
    swap = JS_SWAP.search(head)
    if swap and status in (404, 410) and len(text) < 3000:
        return url.replace(swap.group(1), swap.group(2), 1)
    refresh = META_REFRESH.search(head)
    if refresh and status in (200, 404, 410) and int(refresh.group(1)) <= MAX_REFRESH:
        target = urljoin(url, html.unescape(refresh.group(2)))
        if norm(target) != norm(url):
            return target
    return None


async def read_capped(response: aiohttp.ClientResponse, limit: int, whole=False) -> bytes:
    """Up to `limit` bytes of the body, or whatever arrived before the server hung up or went
    quiet. The status is already in, so a slow page is still an answer, but half a robots.txt
    isn't one."""
    raw = bytearray()
    try:
        async for chunk in response.content.iter_chunked(65536):
            raw += chunk
            if len(raw) >= limit:
                break
    except (aiohttp.ClientPayloadError, TimeoutError):
        if whole:
            raise NoAnswer("robots-error") from None
    return bytes(raw[:limit])


def robots_rules(text: str) -> RobotFileParser:
    """robots.txt as RFC 9309 reads it: a group is ours only if it names our product token
    exactly. The stdlib matches substrings, so a group for "LinkCheck" would catch us."""
    kept, ours, in_rules = [], False, False
    for line in text.splitlines():
        field, _, value = line.split("#", 1)[0].partition(":")
        field = field.strip().lower()
        if field == "user-agent":
            if in_rules:
                ours, in_rules = False, False
                kept.append("")
            token = value.strip().split("/")[0].strip().lower()
            if token in (AGENT, "*"):
                kept.append(f"User-agent: {token}")
                ours = True
        elif field in ("allow", "disallow", "crawl-delay"):
            in_rules = True
            if ours:
                kept.append(line)
    rules = RobotFileParser()
    rules.parse(kept)
    return rules


def retry_after(value: str | None) -> float:
    """How long a server asked us to back off, in seconds or as a date, and never under 30."""
    try:
        wait = float(value or 30)
    except ValueError:
        try:
            wait = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError):
            wait = 60
    return max(wait, 30)


LEGACY_TLS = legacy_tls()


class Gate:
    """One request at a time, `gap` seconds apart."""

    def __init__(self, gap: float):
        self.gap, self.free_at, self.lock = gap, 0.0, asyncio.Lock()

    async def __aenter__(self):
        await self.lock.acquire()
        wait = self.free_at - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)

    async def __aexit__(self, *_):
        self.free_at = max(self.free_at, time.monotonic() + self.gap)
        self.lock.release()

    def hold(self, seconds: float):
        self.free_at = max(self.free_at, time.monotonic() + seconds)

    def wait(self) -> float:
        return self.free_at - time.monotonic()


class Fetcher:
    def __init__(self, session: aiohttp.ClientSession, gap: float = 1.0):
        self.session, self.gap = session, gap
        self.gates: dict[str, Gate] = {}
        self.dns: dict[str, str] = {}
        self.robots: dict[str, RobotFileParser | str] = {}
        self.probes: dict[str, tuple[int, str]] = {}
        self.homes: dict[str, Seen] = {}

    def gate(self, host: str) -> Gate:
        """Each site shares one gate, bar a host that asked for its own crawl-delay."""
        key = host if host in self.gates else site(host)
        if key not in self.gates:
            self.gates[key] = Gate(self.gap)
        return self.gates[key]

    async def lookup(self, host: str) -> str:
        """'' when the host has a public address, else why not. Encoded the way aiohttp will
        connect to it, since the stdlib's older IDNA turns straße.de into strasse.de."""
        if host not in self.dns:
            try:
                ascii_host = URL.build(scheme="http", host=host).raw_host
                loop = asyncio.get_running_loop()
                found = await loop.getaddrinfo(ascii_host, 443, type=socket.SOCK_STREAM)
                self.dns[host] = "" if any(is_public(f[4][0]) for f in found) else "private"
            except socket.gaierror as e:
                if e.errno not in GONE_DNS:
                    return "dns-temp"
                self.dns[host] = "dns"
            except ValueError:
                self.dns[host] = "dns"
        return self.dns[host]

    async def send(
        self, url: str, limit: int, robots=False, tls=None, cookies: dict | None = None
    ) -> Reply:
        """One polite GET, no redirects followed. A site that's asked for more than five minutes'
        peace gets it, and its stories come back rate limited without being asked for."""
        gate = self.gate(urlsplit(url).hostname or "")
        if gate.wait() > MAX_WAIT:
            return Reply(429, None, False, "", {})
        try:
            async with (
                gate,
                self.session.get(
                    url,
                    headers=HEADERS,
                    allow_redirects=False,
                    timeout=TIMEOUT,
                    ssl=tls,
                    cookies=cookies,
                ) as r,
            ):
                kind = r.headers.get("content-type", "").lower()
                is_html = not kind or "html" in kind
                raw = await read_capped(r, limit, whole=robots) if is_html or robots else b""
                text = decode(raw, r.charset)
                if r.status == 429 or (r.status == 503 and "retry-after" in r.headers):
                    gate.hold(retry_after(r.headers.get("retry-after")))
                jar = {n: m.value for n, m in r.cookies.items() if COOKIE_NAME.fullmatch(n)}
                return Reply(r.status, r.headers.get("location"), is_html, text, jar)
        except aiohttp.ClientSSLError:
            if tls is not None:
                raise NoAnswer("tls") from None
            return await self.send(url, limit, robots, LEGACY_TLS, cookies)
        except (TimeoutError, aiohttp.ClientError, OSError, ValueError) as e:
            raise NoAnswer(kind_of(e)) from e

    async def allowed(self, url: str) -> str:
        """'' if robots.txt lets us fetch this, else why not."""
        key = urlsplit(url).netloc.lower()
        rules = self.robots.get(key)
        if rules is None:
            if len(self.robots) > 5000:
                self.robots.clear()
            rules = await self.load_robots(urlsplit(url).scheme + "://" + key)
            if not isinstance(rules, str) or rules in SETTLED:
                self.robots[key] = rules
            if not isinstance(rules, str) and (delay := rules.crawl_delay(AGENT)):
                gap = max(self.gap, min(float(delay), MAX_DELAY))
                gate = self.gates.setdefault(urlsplit(url).hostname or "", Gate(gap))
                gate.gap = gap
                gate.hold(gap)
        if isinstance(rules, str):
            return rules
        return "" if rules.can_fetch(AGENT, url) else "robots"

    async def load_robots(self, base: str) -> RobotFileParser | str:
        url = base + "/robots.txt"
        for _ in range(5):
            problem = await self.lookup(urlsplit(url).hostname or "")
            if problem:
                return problem
            try:
                reply = await self.send(url, MAX_ROBOTS, robots=True)
            except NoAnswer as e:
                return e.kind
            if reply.status in REDIRECTS and reply.location:
                url = urljoin(url, reply.location)
                continue
            if reply.status >= 500 or reply.status == 429:
                return "robots-error"
            return robots_rules(reply.text if 200 <= reply.status < 300 else "")
        return robots_rules("")

    async def get(self, url: str) -> Seen:
        """Follow a URL to wherever it ends up, each hop polite to its own host. Cookies only
        last the one chain, so a site's cookie check can pass without us keeping anything."""
        current, hops, gone, jars = url, 0, 0, defaultdict(dict)
        for _ in range(MAX_HOPS):
            try:
                parts = urlsplit(current)
                usable = parts.scheme in ("http", "https") and parts.hostname
            except ValueError:
                usable = False
            if not usable:
                return Seen(current, hops=hops, error="badurl")
            problem = await self.lookup(parts.hostname) or await self.allowed(current)
            if problem:
                return Seen(current, hops=hops, error=problem)
            jar = jars[site(parts.hostname)]
            for _ in range(3):
                try:
                    reply = await self.send(current, MAX_BODY, cookies=jar)
                except NoAnswer as e:
                    return Seen(current, hops=hops, error=e.kind)
                jar.update(reply.cookies)
                if reply.status != 429:
                    break
            target = next_hop(current, reply.status, reply.location, reply.text)
            if target is None:
                text = reply.text
                return Seen(
                    current,
                    reply.status,
                    hops,
                    reply.html,
                    title_of(text),
                    is_parked(text),
                    gone=gone,
                )
            if reply.status in (404, 410):
                gone = reply.status
            current, hops = target, hops + 1
        return Seen(current, hops=hops, error="loop")

    async def home(self, origin: str) -> Seen:
        """What the host's home page says, asked once per host."""
        if origin not in self.homes:
            if len(self.homes) > 20_000:
                self.homes.clear()
            self.homes[origin] = await self.get(origin + "/")
        return self.homes[origin]

    async def probe(self, url: str) -> tuple[int, str]:
        """Status and title of a path that can't exist on this host, asked once per host."""
        host = urlsplit(url).hostname or ""
        if host not in self.probes:
            if len(self.probes) > 20_000:
                self.probes.clear()
            made_up = f"{urlsplit(url).scheme}://{host}/hn-afterlife-{zlib.crc32(host.encode())}"
            seen = await self.get(made_up)
            self.probes[host] = (seen.status, seen.title)
        return self.probes[host]


def session() -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(
        resolver=PublicResolver(), limit=0, limit_per_host=2, ttl_dns_cache=300
    )
    return aiohttp.ClientSession(
        connector=connector,
        cookie_jar=aiohttp.DummyCookieJar(),
        max_line_size=65536,
        max_field_size=65536,
    )
