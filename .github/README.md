<h1 align="center">Hacker Afterlife</h1>
<p align="center">
<i>Every link that made Hacker News since 2007, checked to see which still work, which moved and which died</i>
</p>

<details>
  <summary>Contents</summary>

- [About](#about)
- [The crawler](#the-crawler)
- [Development](#development)
- [Credits](#credits)

</details>

## About

Old HN threads still get read, and the links at the top of them rot. This checks the link on every story that got 100 or more points, plus each day's top 30, and sorts it into one of five fates:

- Alive - it's still there, at the same address
- Moved - it redirects to a page that's clearly still the story
- Dead - the domain's gone, it's a 404 or 410, or it didn't answer twice, a week apart
- Lands elsewhere - it redirects to a home page, a parking page or something that isn't the story
- Can't tell - a bot wall, a consent page, a server error, or robots.txt asked us not to look

Dead is deliberately narrow. Anything odder than those three plain deaths goes to one of the last two, along with what we saw, so you can judge it yourself.

The site that draws all this (one dot per story, by month) isn't out yet. For now the repo's just the crawler.

---

## The crawler

If you've spotted `hn-afterlife-linkcheck` in your logs, it's this. It looks at each link about once a year, one request at a time per site and a second apart. It reads no more than 400 KB of a page, never runs JavaScript, never pretends to be a browser and never follows a link onto a private address. It obeys robots.txt, so to keep it out, add:

```
User-agent: hn-afterlife-linkcheck
Disallow: /
```

A link it can't check counts as "can't tell", never dead. If it's got something wrong, [tell us which link](https://github.com/NotAFlightRisk/afterlife/issues/new?template=wrong_verdict.yml) and we'll sort it.

GitHub repos and issues are checked through GitHub's API, and YouTube videos and X posts through their oEmbed endpoints, since those answer more reliably than the pages do.

---

## Development

You'll need [uv](https://docs.astral.sh/uv/) and [Git](https://git-scm.com/). The crawler is Python, and lives in `crawler/`.

```bash
git clone git@github.com:NotAFlightRisk/afterlife.git
cd afterlife
uv run --project crawler afterlife stories
uv run --project crawler afterlife crawl
uv run --project crawler afterlife stats
```

`stories` pulls the story list from [Algolia's HN API](https://hn.algolia.com/api), `crawl` checks every link (a day or so for the lot), and `stats` prints how each year's links are doing. It all lives in `data/afterlife.db`. Run `crawl` again a week later and anything that didn't answer gets its second try.

The tests are `uv run --project crawler pytest`, and lint is `uv run --project crawler ruff check`.

---

## Credits

##### Contributors

[![contributors badge](https://readme-contribs.as93.net/contributors/NotAFlightRisk/afterlife?shape=squircle)](https://github.com/NotAFlightRisk/afterlife/graphs/contributors)

Story data comes from [Algolia's HN Search API](https://hn.algolia.com/api), and the archived copies from the [Internet Archive's Wayback Machine](https://web.archive.org/).

---

<!-- License + Copyright -->
<p  align="center">
  <a href="https://github.com/NotAFlightRisk"><img width="64" src="https://pixelflare.cc/iain/gif/penguin-dance.gif" /></a><br>
  <sup>
    <i>Licensed under <a href="../LICENSE">MIT</a>, © <a href="https://peng.ly">NotAFlightRisk</a> 2026</i>
  </sup>
</p>

<!--
oooh, hello there! hope you're having a nice day :)
   |\__      |\___
 (:> __)X  (:o ___(
   |/        |/
-->
