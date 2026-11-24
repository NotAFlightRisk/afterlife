<script lang="ts">
  import { tick } from 'svelte';
  import Curve from '#lib/components/Curve.svelte';
  import Fate from '#lib/components/Fate.svelte';
  import StoryCard from '#lib/components/StoryCard.svelte';
  import YearGrid from '#lib/components/YearGrid.svelte';
  import { fateOf, loadCard, type Card, type Dot } from '#lib/data.ts';
  import { FATES } from '#lib/fates.ts';
  import { count, date, inTen, plural } from '#lib/format.ts';

  let { data } = $props();

  const MONTHS = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec'
  ];
  const years = $derived(Object.entries(data.stats.years));
  const totals = $derived(
    FATES.map((fate) => [fate, years.reduce((sum, [, counts]) => sum + counts[fate], 0)] as const)
  );
  const checked = $derived(totals.reduce((sum, [, n]) => sum + n, 0));
  const [first, oldest] = $derived(years[0]);
  const oldestTotal = $derived(Object.values(oldest).reduce((sum, n) => sum + n, 0));
  const headline = $derived(
    `About ${inTen(oldest.dead, oldestTotal)} of the links HN read in ${first} are dead`
  );

  let hovered = $state<{ dot: Dot; x: number; y: number }>();
  let card = $state<Card>();
  let panel = $state<HTMLElement>();

  const monthSizes = (year: string) =>
    MONTHS.map(
      (_, month) => data.stats.months[`${year}-${String(month + 1).padStart(2, '0')}`] ?? 0
    );

  async function pick(id: number) {
    hovered = undefined;
    card = await loadCard(id);
    await tick();
    panel?.querySelector<HTMLElement>('[tabindex="-1"]')?.focus();
  }
</script>

<svelte:head>
  <title>Hacker Afterlife: what became of every link on Hacker News</title>
  <meta
    name="description"
    content="{headline}. Every link that made Hacker News since 2007, checked and drawn as one dot each, with the Wayback copy for the ones that died."
  />
  <meta property="og:title" content="{headline}." />
  <meta
    property="og:description"
    content="Every link that made Hacker News since 2007, one dot each."
  />
  <meta property="og:image" content="https://afterlife.peng.ly/og.png" />
  <meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<svelte:window onkeydown={(event) => event.key === 'Escape' && (card = undefined)} />

<section class="intro" aria-labelledby="headline">
  <h1 id="headline">{headline}.</h1>
  <p>
    Plain deaths only: the domain's gone, a 404 or 410, or no answer twice, a week apart. Another
    {inTen(oldest.elsewhere, oldestTotal)} now land somewhere that isn't the story.
  </p>
  <Curve {years} />
  <ul class="legend" aria-label="What the colours mean">
    {#each totals as [fate, n] (fate)}
      <li><Fate {fate} /> {count(n)}</li>
    {/each}
  </ul>
</section>

<section class="grid" aria-labelledby="grid-title">
  <div class="grid-head">
    <h2 id="grid-title">Every story, one dot each</h2>
    <p>
      {count(checked)} links by the month they were posted, as our crawler found them by
      {date(data.stats.checked)}. Hover for the story, click for what happened to it.
    </p>
  </div>
  <div class="months" aria-hidden="true">
    {#each MONTHS as month (month)}<span>{month}</span>{/each}
  </div>
  {#each years as [year, counts] (year)}
    <YearGrid
      {year}
      {counts}
      months={monthSizes(year)}
      onpick={pick}
      onhover={(dot, x, y) => (hovered = dot && { dot, x, y })}
    />
  {/each}
</section>

{#if hovered}
  <div class="tip" style:left="{hovered.x}px" style:top="{hovered.y}px" aria-hidden="true">
    <strong>{hovered.dot[4]}</strong>
    <span>
      {plural(hovered.dot[2], 'point')} | {date(hovered.dot[1])} | <Fate
        fate={fateOf(hovered.dot[3])}
      />
    </span>
  </div>
{/if}

{#if card}
  <aside class="panel" bind:this={panel} aria-label="Story">
    <button type="button" class="close" onclick={() => (card = undefined)}>close</button>
    <StoryCard {card} />
    <a class="permalink" href="/lookup?q={card.id}">link to this card</a>
  </aside>
{/if}

<style>
  .intro {
    display: grid;
    gap: var(--space-3);
    max-inline-size: 44rem;

    h1 {
      font-size: var(--size-xl);
    }

    > p {
      max-inline-size: var(--measure);
      color: var(--text-muted);
    }
  }

  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1) var(--space-4);
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--size-xs);
    font-variant-numeric: tabular-nums;
  }

  .grid {
    display: grid;
    gap: var(--space-4);
    --label: 6rem;
    margin-block-start: var(--space-6);
  }

  .grid-head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--space-1) var(--space-3);

    h2 {
      font-size: var(--size-m);
    }

    p {
      color: var(--text-muted);
      font-size: var(--size-xs);
    }
  }

  .months {
    position: sticky;
    inset-block-start: 0;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: var(--month-gap);
    margin-inline-start: calc(var(--label) + var(--space-4));
    padding-block: var(--space-1);
    background: var(--surface);
    color: var(--text-muted);
    font-size: var(--size-xs);
  }

  .tip {
    position: fixed;
    z-index: 3;
    display: grid;
    gap: var(--space-1);
    max-inline-size: 20rem;
    padding: var(--space-2) var(--space-3);
    translate: 12px 12px;
    background: var(--surface);
    border: 1px solid var(--edge);
    box-shadow: 0 2px 8px rgb(0 0 0 / 0.15);
    font-size: var(--size-xs);
    pointer-events: none;

    span {
      color: var(--text-muted);
    }
  }

  .panel {
    position: fixed;
    z-index: 2;
    inset: auto var(--gutter) var(--gutter) auto;
    display: grid;
    gap: var(--space-3);
    inline-size: min(24rem, 100% - 2 * var(--gutter));
    max-block-size: calc(100dvh - 2 * var(--gutter));
    overflow: auto;
    padding: var(--space-4);
    background: var(--surface);
    border: 1px solid var(--edge);
    box-shadow: 0 4px 16px rgb(0 0 0 / 0.18);
    overscroll-behavior: contain;
  }

  .close,
  .permalink {
    justify-self: end;
    padding: 0;
    border: 0;
    background: none;
    color: var(--text-muted);
    font-size: var(--size-xs);
    text-decoration: underline;
    cursor: pointer;
  }

  .close {
    margin-block-end: calc(-1 * var(--space-2));
  }

  @media (max-width: 40rem) {
    .months {
      margin-inline-start: 0;
      font-size: var(--size-2xs);
    }

    .panel {
      inset: auto 0 0;
      inline-size: 100%;
      max-block-size: 60dvh;
      border-inline: 0;
      border-block-end: 0;
    }
  }
</style>
