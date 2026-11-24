<script lang="ts">
  import { browser } from '$app/env';
  import { page } from '$app/state';
  import StoryRows from '#lib/components/StoryRows.svelte';
  import { loadDay, type Card } from '#lib/data.ts';
  import { works } from '#lib/fates.ts';
  import { date, shift, today, yearsBefore, type Step } from '#lib/format.ts';

  let { data } = $props();

  interface Column {
    day: string;
    ago?: number;
    stories?: Card[];
    front?: boolean;
  }

  const [earliest, latest] = $derived(data.stats.days);
  const asked = $derived(browser ? page.url.searchParams.get('d') : null);
  const picked = $derived(asked && asked >= earliest && asked <= latest ? asked : null);
  let columns = $state<Column[]>([]);

  $effect(() => {
    if (!browser) return;
    const wanted: Column[] = picked
      ? [{ day: picked }]
      : [5, 10, 15].map((ago) => ({ day: yearsBefore(today(), ago), ago }));
    columns = wanted;
    let current = true;
    wanted.forEach((column, index) =>
      loadDay(column.day).then((found) => {
        if (current)
          columns[index] = { ...column, stories: found?.stories ?? [], front: found?.front };
      })
    );
    return () => (current = false);
  });

  function still(stories: Card[]) {
    const linked = stories.filter((story) => story.url);
    return `${linked.filter((story) => works(story.fate)).length} of ${linked.length} links still work`;
  }
</script>

<svelte:head>
  <title>This day on Hacker News, 5, 10 and 15 years ago | Hacker Afterlife</title>
  <meta
    name="description"
    content="Hacker News's top stories from 5, 10 and 15 years ago today, and how many of their links still work."
  />
</svelte:head>

{#snippet step(label: string, by: Step)}
  {@const day = shift(picked ?? latest, by)}
  {#if day >= earliest && day <= latest}<a href="/day?d={day}">{label}</a>{:else}{label}{/if}
{/snippet}

<div class="day">
  <header>
    <h1 id="day-title">
      {picked ? `Hacker News on ${date(picked)}` : 'This day, 5, 10 and 15 years ago'}
    </h1>
    <p>
      Where we've got HN's own front page for a day, that's what you get. Otherwise it's that day's
      top 30 stories by points, which is close but not quite it. Dead links go to their Wayback copy
      instead.
    </p>
    {#if picked}
      <p class="step">
        Go back a {@render step('day', { days: -1 })}, {@render step('month', { months: -1 })} or
        {@render step('year', { years: -1 })}. Go forward a {@render step('day', { days: 1 })},
        {@render step('month', { months: 1 })} or {@render step('year', { years: 1 })}.
      </p>
    {/if}
    <form method="GET" action="/day">
      <label for="day">Any other day</label>
      <input id="day" name="d" type="date" min={earliest} max={latest} value={picked} required />
      <button type="submit">show me</button>
      {#if picked}<a href="/day">back to today</a>{/if}
    </form>
  </header>

  <div class="columns" class:single={picked}>
    {#each columns as column (column.day)}
      <section aria-labelledby={column.ago ? `day-${column.day}` : 'day-title'}>
        {#if column.ago}
          <h2 id="day-{column.day}">{column.ago} years ago <span>{date(column.day)}</span></h2>
        {/if}
        {#if !column.stories}
          <p class="quiet">Loading...</p>
        {:else if column.stories.length}
          <p class="still">
            {still(column.stories)}
            <span>{column.front ? "HN's front page" : 'top 30 by points'}</span>
          </p>
          <StoryRows stories={column.stories} />
        {:else}
          <p class="quiet">Nothing made it from that day. HN was a quiet place back then.</p>
        {/if}
      </section>
    {:else}
      <p class="quiet">Working out what day it is where you are...</p>
    {/each}
  </div>
</div>

<style>
  .day,
  header {
    display: grid;
    gap: var(--space-4);
  }

  header {
    gap: var(--space-2);

    h1 {
      font-size: var(--size-l);
    }

    p {
      max-inline-size: var(--measure);
      color: var(--text-muted);
    }
  }

  form {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--size-s);

    a {
      text-decoration: underline;
    }
  }

  .columns {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
    gap: var(--space-6);

    &.single {
      max-inline-size: 44rem;
    }
  }

  section {
    display: grid;
    align-content: start;
    gap: var(--space-2);

    h2 {
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
      align-items: baseline;
      font-size: var(--size-m);

      span {
        color: var(--text-muted);
        font-size: var(--size-xs);
        font-weight: normal;
      }
    }
  }

  .step a {
    text-decoration: underline;
  }

  .still {
    font-weight: bold;
    font-size: var(--size-s);

    span {
      color: var(--text-muted);
      font-size: var(--size-xs);
      font-weight: normal;
    }
  }

  .quiet {
    color: var(--text-muted);
  }
</style>
