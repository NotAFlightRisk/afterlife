<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/state';
  import StoryRows from '#lib/components/StoryRows.svelte';
  import { fateOf, type Row } from '#lib/data.ts';
  import { count, percent } from '#lib/format.ts';

  let { data } = $props();

  const LISTS = [
    { id: 'upvoted', label: 'dead links' },
    { id: 'hosts', label: 'domains' },
    { id: 'launches', label: 'Show HN cemetery' }
  ] as const;

  let shown = $state<(typeof LISTS)[number]['id']>('upvoted');

  onMount(() => {
    shown = LISTS.find((list) => list.id === page.url.searchParams.get('show'))?.id ?? shown;
  });

  const stories = (rows: Row[]) =>
    rows.map(([id, day, points, fate, title, url]) => ({
      id,
      day,
      points,
      title,
      url,
      fate: fateOf(fate)
    }));
</script>

<svelte:head>
  <title>The Hacker News graveyard | Hacker Afterlife</title>
  <meta
    name="description"
    content="The most upvoted Hacker News links that are dead now, the domains that took the most HN history with them, and the Show HN launches that don't load any more."
  />
</svelte:head>

<div class="graveyard">
  <h1>The graveyard</h1>
  <div class="switch" role="group" aria-label="Which list">
    {#each LISTS as list (list)}
      <button type="button" aria-pressed={shown === list.id} onclick={() => (shown = list.id)}>
        {list.label}
      </button>
    {/each}
  </div>

  {#if shown === 'upvoted'}
    <p>The most upvoted stories whose links are dead now. Each one goes to its Wayback copy.</p>
    <StoryRows stories={stories(data.upvoted)} dated />
  {:else if shown === 'hosts'}
    <p>
      The domains that took the most HN history with them: their stories are dead or land somewhere
      else now. Some are shut, some just moved everything without redirects.
    </p>
    <table>
      <thead>
        <tr>
          <th scope="col">domain</th>
          <th scope="col">dead</th>
          <th scope="col">elsewhere</th>
          <th scope="col">stories</th>
          <th scope="col">gone</th>
        </tr>
      </thead>
      <tbody>
        {#each data.hosts as host (host)}
          <tr>
            <th scope="row">
              <a href="/domain/{host.host}">
                {#each host.host.split('.') as label, index (index)}{#if index}.<wbr
                    />{/if}{label}{/each}
              </a>
            </th>
            <td>{count(host.dead)}</td>
            <td>{count(host.elsewhere)}</td>
            <td>{count(host.stories)}</td>
            <td>{percent(host.dead + host.elsewhere, host.stories)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p>Show HN launches whose links are dead or land somewhere else now, biggest first.</p>
    <StoryRows stories={stories(data.launches)} dated />
  {/if}
</div>

<style>
  .graveyard {
    display: grid;
    gap: var(--space-3);
    max-inline-size: 50rem;

    > p {
      color: var(--text-muted);
    }
  }

  h1 {
    font-size: var(--size-l);
  }

  table {
    justify-self: start;
    font-size: var(--size-s);

    th,
    td {
      padding: 0.2rem var(--space-3) 0.2rem 0;
      text-align: end;
    }

    :is(th[scope='row'], th:first-child) {
      text-align: start;
      font-weight: normal;
    }

    thead th {
      color: var(--text-muted);
      font-size: var(--size-xs);
      font-weight: normal;
    }

    tbody tr:hover {
      background: var(--surface-sunk);
    }
  }
</style>
