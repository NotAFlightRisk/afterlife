<script lang="ts">
  import { destination, hostOf, thread } from '#lib/data.ts';
  import { works, type Fate as FateName } from '#lib/fates.ts';
  import { date, plural } from '#lib/format.ts';
  import Fate from './Fate.svelte';

  interface Story {
    id: number;
    title: string;
    day: string;
    points: number;
    url?: string;
    comments?: number;
    fate?: FateName;
    final?: string;
  }

  let { stories, dated = false }: { stories: Story[]; dated?: boolean } = $props();
</script>

<ol class="rows">
  {#each stories as story (story)}
    <li>
      <div class="title">
        <a href={destination(story)} rel="nofollow noopener noreferrer">{story.title}</a>
        {#if story.url}
          <span class="host">({hostOf(story.url)}{works(story.fate) ? '' : ', archived'})</span>
        {/if}
      </div>
      <div class="sub">
        <Fate fate={story.fate} />
        <span>{plural(story.points, 'point')}</span>
        {#if dated}<span>{date(story.day)}</span>{/if}
        {#if story.comments !== undefined}
          <a href={thread(story.id)}>{plural(story.comments, 'comment')}</a>
        {:else}
          <a href={thread(story.id)}>thread</a>
        {/if}
        <a href="/lookup?q={story.id}">card</a>
      </div>
    </li>
  {/each}
</ol>

<style>
  .rows {
    display: grid;
    gap: var(--space-2);
    margin: 0;
    padding-inline-start: 2.6em;
    font-variant-numeric: tabular-nums;

    ::marker {
      color: var(--text-muted);
    }
  }

  .title {
    overflow-wrap: anywhere;
  }

  .host,
  .sub {
    color: var(--text-muted);
    font-size: var(--size-xs);
  }

  .sub {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--space-2);

    > :not(:first-child)::before {
      content: '|';
      margin-inline-end: var(--space-2);
      color: var(--rule);
    }

    a:hover {
      color: var(--text);
    }
  }
</style>
