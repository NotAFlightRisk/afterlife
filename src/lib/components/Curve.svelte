<script lang="ts">
  import Fate from '#lib/components/Fate.svelte';
  import type { Fate as FateName } from '#lib/fates.ts';
  import { count, percent } from '#lib/format.ts';

  let { years }: { years: [string, Record<FateName, number>][] } = $props();

  // bottom to top, the way the grid stacks its dots
  const STACK: FateName[] = ['dead', 'elsewhere', 'unsure', 'moved', 'alive'];
  const BROKEN: FateName[] = ['dead', 'elsewhere'];
  const ROWS = [...STACK].reverse();
  const TICKS = [25, 50, 75];

  let all = $state(false);
  let hovered = $state<{ index: number; x: number; y: number }>();
  const top = $derived(all ? 1 : 0.5);
  const totals = $derived(
    years.map(([, counts]) => Object.values(counts).reduce((sum, n) => sum + n, 0))
  );

  const x = (index: number) => (index / (years.length - 1)) * 100;
  const y = (share: number) => 100 - (share / top) * 100;

  // clip-path polygons, top edge then bottom edge. Hidden bands lie flat on the broken ones,
  // so switching views grows them in place
  const bands = $derived.by(() => {
    const under = years.map(() => 0);
    const edge = () => under.map((share, index) => `${x(index)}% ${y(share)}%`);
    return STACK.map((fate) => {
      const bottom = edge().reverse();
      if (all || BROKEN.includes(fate)) {
        years.forEach(([, counts], index) => (under[index] += counts[fate] / totals[index]));
      }
      return { fate, points: [...edge(), ...bottom].join(', ') };
    });
  });

  function split(index: number) {
    const [year, counts] = years[index];
    const share = (n: number) => percent(n, totals[index]);
    return (
      `${year}'s links: ${share(counts.alive + counts.moved)} still work, ` +
      `${share(counts.dead + counts.elsewhere)} are broken (${share(counts.dead)} dead) ` +
      `and we can't tell for ${share(counts.unsure)}.`
    );
  }
  const summary = $derived.by(() => {
    const last = years.length - 1;
    if (all) return `${split(0)} ${split(last)}`;
    const [[from, oldest], [to, newest]] = [years[0], years[last]];
    return (
      `Dead links as a share of each year's: ${percent(oldest.dead, totals[0])} for ${from}, ` +
      `falling to ${percent(newest.dead, totals[last])} for ${to}. Links that land elsewhere ` +
      `sit on top, ${percent(oldest.elsewhere, totals[0])} more for ${from}.`
    );
  });

  function hover(event: PointerEvent & { currentTarget: HTMLElement }) {
    const area = event.currentTarget.getBoundingClientRect();
    const along = (event.clientX - area.left) / area.width;
    const index = Math.round(Math.min(1, Math.max(0, along)) * (years.length - 1));
    hovered = { index, x: event.clientX, y: event.clientY };
  }
</script>

<figure class="curve">
  <div class="views" role="group" aria-label="What the chart shows">
    <button type="button" aria-pressed={!all} onclick={() => (all = false)}>broken links</button>
    <button type="button" aria-pressed={all} onclick={() => (all = true)}>all links</button>
  </div>
  <div class="chart" role="img" aria-label={summary}>
    <div class="line" style:inset-block-start="{y(0.25)}%"></div>
    {#each bands as band (band.fate)}
      <div class="band {band.fate}" style:clip-path="polygon({band.points})"></div>
    {/each}
    {#each TICKS as tick (tick)}
      {@const at = y(tick / 100)}
      <span class="tick" class:off={at < 0} style:inset-block-start="{at}%">{tick}%</span>
    {/each}
    {#if hovered}
      <div class="cursor" style:inset-inline-start="{x(hovered.index)}%"></div>
    {/if}
    <div
      class="hit"
      aria-hidden="true"
      onpointermove={hover}
      onpointerleave={() => (hovered = undefined)}
    ></div>
  </div>
  {#if hovered}
    {@const [year, counts] = years[hovered.index]}
    {@const total = totals[hovered.index]}
    <div
      class="tip"
      class:flip={hovered.index > (years.length - 1) / 2}
      style:left="{hovered.x}px"
      style:top="{hovered.y}px"
      aria-hidden="true"
    >
      <p><strong>{year}</strong> <span>| {count(total)} links</span></p>
      <table>
        <tbody>
          {#each ROWS as fate (fate)}
            <tr>
              <td><Fate {fate} /></td>
              <td>{count(counts[fate])}</td>
              <td>{percent(counts[fate], total)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
  <figcaption>
    <span>{years[0][0]}</span>
    <span>
      {all
        ? 'by year posted, broken at the bottom'
        : 'dead, with lands elsewhere on top, by year posted'}
    </span>
    <span>{years.at(-1)![0]}</span>
  </figcaption>
</figure>

<style>
  .curve {
    --move: 0.7s cubic-bezier(0.65, 0, 0.35, 1);
    display: grid;
    gap: var(--space-1);
    margin: 0;
    padding-inline-end: 2.25rem;
  }

  .views {
    display: flex;
    justify-self: end;
    font-size: var(--size-xs);

    button {
      padding: 0;
      border: 0;
      background: none;
      color: var(--text-muted);
      cursor: pointer;

      &:hover {
        text-decoration: underline;
      }
    }

    button + button::before {
      content: '|';
      content: '|' / '';
      display: inline-block;
      padding-inline: 0.4em;
      color: var(--text-muted);
      font-weight: normal;
    }

    [aria-pressed='true'] {
      color: var(--text);
      font-weight: bold;
    }
  }

  .chart {
    position: relative;
    block-size: clamp(4rem, 3rem + 5vw, 6rem);
    border-block-end: 1px solid var(--edge);
  }

  .line {
    position: absolute;
    inset-inline: 0;
    border-block-start: 1px dashed var(--rule);
    transition: inset-block-start var(--move);
  }

  .band {
    position: absolute;
    inset: 0;
    transition: clip-path var(--move);
  }

  .dead {
    background: var(--fate-dead);
  }

  .elsewhere {
    background: var(--fate-elsewhere);
  }

  .unsure {
    background: var(--hatch), var(--surface-sunk);
  }

  .moved {
    background: var(--fate-moved);
  }

  .alive {
    background: var(--fate-alive);
  }

  .tick {
    position: absolute;
    inset-inline-start: 100%;
    translate: 0 -50%;
    padding-inline-start: var(--space-1);
    color: var(--text-muted);
    font-size: var(--size-xs);
    line-height: 1;
    transition:
      inset-block-start var(--move),
      opacity var(--move);

    &.off {
      opacity: 0;
    }
  }

  .cursor {
    position: absolute;
    inset-block: 0;
    inline-size: 1px;
    background: var(--text);
    box-shadow: 0 0 0 1px var(--surface);
  }

  .hit {
    position: absolute;
    inset: 0;
  }

  .tip {
    &.flip {
      translate: calc(-100% - 12px) 12px;
    }

    span {
      color: var(--text-muted);
    }

    td + td {
      padding-inline-start: var(--space-3);
      text-align: end;
    }
  }

  figcaption {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 0 var(--space-2);
    color: var(--text-muted);
    font-size: var(--size-xs);
    text-align: center;

    @media (max-width: 40rem) {
      span:nth-child(2) {
        order: 1;
        flex-basis: 100%;
      }
    }
  }
</style>
