<h1 align="center">Hacker Afterlife</h1>
<p align="center">
<i>Every link that made Hacker News since 2007, checked to see which still work, which moved and which died</i>
</p>
<p align="center">
<a href="https://afterlife.peng.ly"><b>afterlife.peng.ly</b></a>
</p>

<details>
  <summary>Contents</summary>

- [About](#about)
- [The crawler](#the-crawler)
- [The data](#the-data)
- [Development](#development)
- [Deploying](#deploying)
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

The site draws every story as one dot by the month it was posted. Click one for what happened to it and its Wayback copy, or head to [this day](https://afterlife.peng.ly/day) for HN's top stories from 5, 10 and 15 years ago today. You can [look up](https://afterlife.peng.ly/lookup) a thread or link, see how any domain's doing at `/domain/<host>`, or browse [the graveyard](https://afterlife.peng.ly/graveyard). There's an [RSS feed](https://afterlife.peng.ly/day.xml) of HN ten years ago today, too.

---

## The crawler

If you've spotted `hn-afterlife-linkcheck` in your logs, it's this. It looks at each link about once a year, one request at a time per site and a second apart. It reads no more than 400 KB of a page, never runs JavaScript, never pretends to be a browser and never follows a link onto a private address. It obeys robots.txt, so to keep it out, add:

```
User-agent: hn-afterlife-linkcheck
Disallow: /
```

A link it can't check counts as "can't tell", never dead. If it's got something wrong, [tell us which link](https://github.com/NotAFlightRisk/afterlife/issues/new?template=wrong_verdict.yml) and we'll sort it. Anything else, it's hackerafterlife@peng.ly.

GitHub repos and issues are checked through GitHub's API, and YouTube videos and X posts through their oEmbed endpoints, since those answer more reliably than the pages do.

---

## The data

Every verdict is in [one CSV](https://afterlife.peng.ly/data/afterlife.csv.gz) (HN id, link, fate and the day it was checked) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and each release has a copy too. It has no reasons in it, and the site says "doesn't answer" for a gone domain and a dead server alike, so none of this is a list of domains up for grabs.

---

## Development

You'll need [uv](https://docs.astral.sh/uv/), [Node](https://nodejs.org/) 22+ and [Git](https://git-scm.com/). The crawler's Python and lives in `crawler/`, and the site's SvelteKit at the root.

```bash
git clone git@github.com:NotAFlightRisk/afterlife.git
cd afterlife
uv run --project crawler afterlife stories
uv run --project crawler afterlife crawl
uv run --project crawler afterlife stats
```

`stories` pulls the story list from [Algolia's HN API](https://hn.algolia.com/api), `crawl` checks every link (a day or so the first time) and `stats` prints how each year's links are doing. It all lives in `data/afterlife.db`. Run `crawl` again a week later and anything that didn't answer gets its second try, and `crawl --recheck` also takes another look at this week's fifty-second of the stories.

`wayback` then asks the [Wayback Machine](https://web.archive.org/) about two kinds of link, at the 15 or so a minute it allows. Home pages that no longer look like the story get compared with their capture from around the day they were posted, and links behind a wall get the newest capture that isn't one. That's a couple of days for the first pass. `fronts` saves HN's own front page for the coming week, 5, 10 and 15 years back, and `run` does `stories`, `crawl` and `wayback` in one go. Both `crawl` and `wayback` take `--minutes` to stop on time.

If you change how links get sorted, `reclassify` re-runs the rules over every check that's already stored, so there's no need to crawl again.

For the site, `build` turns the database into the static files it reads, then it's the usual:

```bash
uv run --project crawler afterlife build
npm install
npm run dev
```

Tests are `uv run --project crawler pytest` and `npm test`, lint is `uv run --project crawler ruff check`, and types are `npm run check`.

---

## Deploying

The site's static apart from the RSS feed, which a tiny Worker builds from the day files on request, so it runs on Cloudflare Workers with static assets. Ours deploys through the 🚀 Deploy workflow, which pulls the crawl's database from a private R2 bucket, builds the data and the site, and runs `wrangler deploy` with `wrangler.jsonc`. Once a week the same workflow re-checks a slice of the stories and puts the database back, when the `CRAWL_HERE` repo variable is `true`.

To run your own, crawl as above, then `npm run build` and `npx wrangler deploy` (change the route in `wrangler.jsonc` first). Without Wrangler, `build/` works on any static host, minus the feed and the `/domain/` pages, which need `_redirects` support.

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
