<script lang="ts">
  import Fate from '#lib/components/Fate.svelte';
  import { FATES } from '#lib/fates.ts';
  import { count, date, percent } from '#lib/format.ts';

  let { data } = $props();

  const AGENT = 'hn-afterlife-linkcheck';
  const years = $derived(
    Object.entries(data.stats.years).map(([year, counts]) => ({
      year,
      counts,
      total: Object.values(counts).reduce((sum, n) => sum + n, 0)
    }))
  );
  const analytics = Boolean(import.meta.env.PUBLIC_PLAUSIBLE_SCRIPT);
  const errors = Boolean(import.meta.env.PUBLIC_SENTRY_DSN);
</script>

<svelte:head>
  <title>About Hacker Afterlife: how every HN link gets checked</title>
  <meta
    name="description"
    content="How Hacker Afterlife checks every link that made Hacker News, what each fate means, the numbers by year, and how to keep its crawler out."
  />
</svelte:head>

<article class="about">
  <h1>About Hacker Afterlife</h1>
  <p>
    Old HN threads still get read, and the links at the top of them rot. This checks the link on
    every story that got 100 or more points since 2007, plus each day's top 30 (back when hardly
    anything reached 100), and sorts each one into one of five fates.
  </p>

  <h2>What the fates mean</h2>
  <dl>
    <dt><Fate fate="alive" /></dt>
    <dd>It's still there, at the same address.</dd>
    <dt><Fate fate="moved" /></dt>
    <dd>It redirects to a page whose title or address still matches the story.</dd>
    <dt><Fate fate="dead" /></dt>
    <dd>
      The domain's gone, the site says 404 or 410, or it didn't answer twice, a week apart. Nothing
      else counts as dead, and a gone domain reads the same as a dead server, on purpose.
    </dd>
    <dt><Fate fate="elsewhere" /></dt>
    <dd>
      It redirects to a home page, an index, a parking page or something that isn't the story. About
      half of these really are gone, and the rest moved somewhere our checks couldn't match.
    </dd>
    <dt><Fate fate="unsure" /></dt>
    <dd>
      A bot wall, a consent page, a server error, a page that says yes to any made-up address, or a
      robots.txt that asked us not to look. These are hatched in the grid, and where the Wayback
      Machine has a copy, the colour under the hatching is what its newest copy found: pale if the
      page was there, black if it was already gone.
    </dd>
  </dl>
  <p>
    Every number here is a snapshot by the year a story was posted. 2009's links have had longer to
    die than 2019's, but they were different links too, so there's no half-life in here.
  </p>

  <h2>The numbers</h2>
  <div class="table">
    <table>
      <thead>
        <tr>
          <th scope="col">posted</th>
          <th scope="col">links</th>
          {#each FATES as fate (fate)}<th scope="col"><Fate {fate} /></th>{/each}
          <th scope="col">dead</th>
        </tr>
      </thead>
      <tbody>
        {#each years as { year, counts, total } (year)}
          <tr>
            <th scope="row">{year}</th>
            <td>{count(total)}</td>
            {#each FATES as fate (fate)}<td>{count(counts[fate])}</td>{/each}
            <td>{percent(counts.dead, total)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="note">As our crawler saw them by {date(data.stats.checked)}.</p>

  <h2>How sure is "dead"?</h2>
  <p>
    Before building this, we checked two fresh samples of 200 stories by hand. Of the links the
    checker called dead for a gone domain, a 404 or 410, or no answer, 57 of 58 really were. Then we
    did it again on this crawl: 50 random dead calls, checked against that rule. 48 were right, one
    was a post that only 404s with a slash on the end, and one we couldn't settle without a browser.
    So the headline is a good estimate, not gospel.
  </p>

  <h2>The crawler</h2>
  <p>
    If you've spotted <code>{AGENT}</code> in your logs, it's this. It looks at each link about once a
    year, one request at a time per site and a second apart. It reads no more than 400 KB of a page, never
    runs JavaScript, never pretends to be a browser and obeys robots.txt. To keep it out, add this to
    yours:
  </p>
  <pre><code
      >User-agent: {AGENT}
Disallow: /</code
    ></pre>
  <p>
    A site it can't check counts as "can't tell", never dead. Anything else, email
    <a href="mailto:hackerafterlife@peng.ly">hackerafterlife@peng.ly</a>.
  </p>

  <h2>The Wayback Machine</h2>
  <p>
    When you open a story card for a link that doesn't work, your browser asks the Internet
    Archive's Wayback Machine for its copy from around the day it was posted. That request goes
    straight from you to archive.org, not through us. Lists link to the Wayback Machine directly,
    which picks the nearest copy itself.
  </p>

  <h2>The data</h2>
  <p>
    <a href="/data/afterlife.csv.gz" download>One CSV</a> (gzipped) of HN id, link, fate and the day
    it was last checked, under
    <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. It has no reasons in it,
    so it's not a list of domains anyone could buy. Titles belong to whoever wrote them.
  </p>

  {#if analytics || errors}
    <h2>Privacy</h2>
    {#if analytics}
      <p>Visits are counted by our own Plausible, with no cookies and nothing personal.</p>
    {/if}
    {#if errors}
      <p>When something breaks, the error goes to our own Bugsink so we can fix it.</p>
    {/if}
  {/if}

  <h2>Got one wrong?</h2>
  <p>
    <a href="https://github.com/NotAFlightRisk/afterlife/issues/new?template=wrong_verdict.yml">
      Tell us which link
    </a>
    and we'll sort it. The code's all on
    <a href="https://github.com/NotAFlightRisk/afterlife">GitHub</a>.
  </p>
</article>

<style>
  .about {
    display: grid;
    gap: var(--space-3);
    max-inline-size: var(--measure);

    h1 {
      font-size: var(--size-l);
    }

    h2 {
      margin-block-start: var(--space-4);
      font-size: var(--size-m);
    }

    a {
      text-decoration: underline;
    }
  }

  dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: var(--space-2) var(--space-4);
    margin: 0;

    dd {
      margin: 0;
    }
  }

  .table {
    overflow-x: auto;
  }

  table {
    font-size: var(--size-xs);

    th,
    td {
      padding: 0.15rem var(--space-3) 0.15rem 0;
      text-align: end;
      white-space: nowrap;
    }

    thead th {
      font-weight: normal;
      color: var(--text-muted);
    }

    th[scope='row'] {
      text-align: start;
    }
  }

  .note {
    color: var(--text-muted);
    font-size: var(--size-xs);
  }

  pre {
    margin: 0;
    padding: var(--space-3);
    overflow-x: auto;
    background: var(--surface-sunk);
    font-size: var(--size-s);
  }

  @media (max-width: 40rem) {
    dl {
      grid-template-columns: 1fr;

      dd {
        margin-block-end: var(--space-2);
      }
    }
  }
</style>
