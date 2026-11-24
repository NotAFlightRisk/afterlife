<script lang="ts">
  import { page } from '$app/state';
  import Fate from '#lib/components/Fate.svelte';
  import StoryRows from '#lib/components/StoryRows.svelte';
  import { fateOf, hostOf, loadHost, type Row } from '#lib/data.ts';
  import { STACKED, works } from '#lib/fates.ts';
  import { count, date } from '#lib/format.ts';

  let { data } = $props();

  const host = $derived(hostOf(`https://${page.params.host ?? ''}`));
  let rows = $state<Row[]>();

  const stories = $derived(
    (rows ?? []).map(([id, day, points, fate, title, url]) => ({
      id,
      day,
      points,
      title,
      url,
      fate: fateOf(fate)
    }))
  );
  const counts = $derived(
    STACKED.map((fate) => [fate, stories.filter((story) => story.fate === fate).length] as const)
  );
  const working = $derived(stories.filter((story) => works(story.fate)).length);

  $effect(() => {
    rows = undefined;
    loadHost(host).then((found) => (rows = found.toSorted((a, b) => a[1].localeCompare(b[1]))));
  });
</script>

<svelte:head>
  <title>{host} on Hacker News: what still loads | Hacker Afterlife</title>
</svelte:head>

<div class="domain">
  <h1>{host}</h1>
  {#if !rows}
    <p class="quiet">Loading...</p>
  {:else if rows.length}
    <p class="score">
      {count(working)} of the {count(rows.length)} links from {host} that made Hacker News still load,
      as our crawler saw it on {date(data.stats.checked)}.
    </p>
    <ul class="counts">
      {#each counts as [fate, n] (fate)}
        {#if n}<li><Fate {fate} /> {count(n)}</li>{/if}
      {/each}
    </ul>
    <StoryRows {stories} dated />
  {:else}
    <p>
      Nothing from {host} got 100 points or made a day's top 30, so it's not in our list. Typo, or just
      a quiet one?
    </p>
  {/if}
</div>

<style>
  .domain {
    display: grid;
    gap: var(--space-3);
    max-inline-size: 50rem;
    overflow-wrap: anywhere;
  }

  h1 {
    font-size: var(--size-l);
  }

  .score {
    font-weight: bold;
  }

  .counts {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1) var(--space-4);
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: var(--size-xs);
  }

  .quiet {
    color: var(--text-muted);
  }
</style>
