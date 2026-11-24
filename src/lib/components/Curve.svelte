<script lang="ts">
  import type { Fate } from '#lib/fates.ts';
  import { percent } from '#lib/format.ts';

  let { years }: { years: [string, Record<Fate, number>][] } = $props();

  const TOP = 0.5;
  const shares = $derived(
    years.map(([year, counts]) => {
      const total = Object.values(counts).reduce((sum, n) => sum + n, 0);
      return { year, dead: counts.dead / total, elsewhere: counts.elsewhere / total };
    })
  );
  const first = $derived(shares[0]);
  const last = $derived(shares.at(-1)!);

  const x = (index: number) => (index / (shares.length - 1)) * 100;
  const y = (share: number) => 100 - (share / TOP) * 100;

  function band(low: (index: number) => number, high: (index: number) => number) {
    const top = shares.map((_, index) => `${x(index)},${y(high(index))}`);
    const bottom = shares.map((_, index) => `${x(index)},${y(low(index))}`).reverse();
    return [...top, ...bottom].join(' ');
  }

  const dead = $derived(
    band(
      () => 0,
      (index) => shares[index].dead
    )
  );
  const elsewhere = $derived(
    band(
      (index) => shares[index].dead,
      (index) => shares[index].dead + shares[index].elsewhere
    )
  );
  const summary = $derived(
    `Dead links as a share of each year's: ${percent(first.dead, 1)} for ${first.year}, ` +
      `falling to ${percent(last.dead, 1)} for ${last.year}. Links that land elsewhere sit ` +
      `on top, ${percent(first.elsewhere, 1)} more for ${first.year}.`
  );
</script>

<figure class="curve">
  <div class="chart" role="img" aria-label={summary}>
    <span class="tick" style:inset-block-start="0">50%</span>
    <span class="tick" style:inset-block-start="50%">25%</span>
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <line x1="0" x2="100" y1="50" y2="50" />
      <polygon class="elsewhere" points={elsewhere} />
      <polygon class="dead" points={dead} />
    </svg>
  </div>
  <figcaption>
    <span>{first.year}</span>
    <span>dead, and lands elsewhere on top, by the year it was posted</span>
    <span>{last.year}</span>
  </figcaption>
</figure>

<style>
  .curve {
    display: grid;
    gap: var(--space-1);
    margin: 0;
  }

  .chart {
    position: relative;
    block-size: clamp(4rem, 3rem + 5vw, 6rem);
    border-block-end: 1px solid var(--fate-elsewhere);
  }

  svg {
    display: block;
    inline-size: 100%;
    block-size: 100%;
  }

  line {
    stroke: var(--rule);
    stroke-dasharray: 2 2;
    vector-effect: non-scaling-stroke;
  }

  .dead {
    fill: var(--fate-dead);
  }

  .elsewhere {
    fill: var(--fate-elsewhere);
  }

  .tick {
    position: absolute;
    inset-inline-end: 0;
    translate: 0 -50%;
    padding-inline-start: var(--space-1);
    background: var(--surface);
    color: var(--text-muted);
    font-size: var(--size-xs);
    line-height: 1;
  }

  figcaption {
    display: flex;
    justify-content: space-between;
    gap: var(--space-2);
    color: var(--text-muted);
    font-size: var(--size-xs);
    text-align: center;
  }
</style>
