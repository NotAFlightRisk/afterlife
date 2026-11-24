<script lang="ts">
  import type { Graveyard } from '#lib/data.ts';
  import { count } from '#lib/format.ts';

  let { hosts }: { hosts: Graveyard['hosts'] } = $props();

  const share = (n: number, stories: number) => `${(n / stories) * 100}%`;
</script>

<section class="hosts" aria-labelledby="hosts-title">
  <h2 id="hosts-title">The domains that took the most with them</h2>
  <ol>
    {#each hosts as { host, dead, elsewhere, stories } (host)}
      <li>
        <a href="/domain/{host}">{host}</a>
        <span class="bar" aria-hidden="true">
          <span class="dead" style:inline-size={share(dead, stories)}></span>
          <span class="elsewhere" style:inline-size={share(elsewhere, stories)}></span>
        </span>
        <span class="gone">
          {count(dead + elsewhere)} of {count(stories)}<span class="visually-hidden"> gone</span>
        </span>
      </li>
    {/each}
  </ol>
  <a class="all" href="/graveyard?show=hosts">all domains</a>
</section>

<style>
  .hosts {
    display: grid;
    gap: var(--space-2);
    font-size: var(--size-xs);
  }

  h2 {
    font-size: var(--size-m);
  }

  ol {
    display: grid;
    grid-template-columns: auto minmax(3rem, 1fr) auto;
    gap: var(--space-1) var(--space-3);
    margin: 0;
    padding: 0;
    list-style: none;
    font-variant-numeric: tabular-nums;
  }

  li {
    display: grid;
    grid-template-columns: subgrid;
    grid-column: 1 / -1;
    align-items: center;
  }

  .bar {
    display: flex;
    block-size: 0.6rem;
    background: var(--surface-sunk);
  }

  .dead {
    background: var(--fate-dead);
  }

  .elsewhere {
    background: var(--fate-elsewhere);
  }

  .gone {
    color: var(--text-muted);
    text-align: end;
  }

  .all {
    justify-self: start;
    color: var(--text-muted);
    text-decoration: underline;
  }
</style>
