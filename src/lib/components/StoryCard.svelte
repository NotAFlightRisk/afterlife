<script lang="ts">
  import { destination, hostOf, thread, type Card } from '#lib/data.ts';
  import { plainWords, works } from '#lib/fates.ts';
  import { count, date, plural } from '#lib/format.ts';
  import Fate from './Fate.svelte';

  let { card, heading = 'h2' }: { card: Card; heading?: 'h1' | 'h2' } = $props();

  interface Capture {
    url: string;
    timestamp: string;
  }

  let capture = $state<Capture | null | undefined>();
  const live = $derived(works(card.fate));
  const lands = $derived(card.final && hostOf(card.final));
  const report = $derived(
    'https://github.com/NotAFlightRisk/afterlife/issues/new?template=wrong_verdict.yml&' +
      new URLSearchParams({ story: thread(card.id), said: plainWords(card.evidence) })
  );

  $effect(() => {
    capture = undefined;
    if (!card.url || live) return;
    const ask = new URL('https://archive.org/wayback/available');
    ask.search = new URLSearchParams({
      url: card.url,
      timestamp: card.day.replaceAll('-', '')
    }).toString();
    const asked = card.id;
    fetch(ask)
      .then((reply) => reply.json())
      .then(({ archived_snapshots }) => {
        const closest = archived_snapshots?.closest;
        if (asked === card.id) capture = closest?.available ? closest : null;
      })
      .catch(() => asked === card.id && (capture = null));
  });
</script>

<article class="story" aria-labelledby="story-{card.id}">
  <svelte:element this={heading} id="story-{card.id}" tabindex="-1">
    {#if card.url && live}
      <a href={destination(card)} rel="nofollow noopener noreferrer">{card.title}</a>
    {:else}
      {card.title}
    {/if}
  </svelte:element>
  <p class="meta">
    {plural(card.points, 'point')} on {date(card.day)} |
    <a href={thread(card.id)}>{plural(card.comments, 'comment')}</a>
  </p>

  {#if card.url}
    <p class="link">{card.url}</p>
    <p class="fate"><Fate fate={card.fate} /> {plainWords(card.evidence)}</p>
    {#if card.fate === 'moved' && card.final}
      <p>
        Now at <a href={card.final} rel="nofollow noopener noreferrer">{lands}</a>{#if card.now}, as
          "{card.now}"{/if}.
      </p>
    {:else if card.fate === 'elsewhere' && lands}
      <p>
        It lands on {lands}{#if card.now}, on a page called "{card.now}"{/if}.
      </p>
    {/if}
    {#if card.was && card.then}
      <p>On {date(card.then)} it was "{card.was}".</p>
    {/if}
    {#if card.captured && card.captured_status === 200}
      <p>Last seen working on {date(card.captured)}, per the Wayback Machine.</p>
    {/if}
    {#if !live}
      <p class="archive" aria-live="polite">
        {#if capture === undefined}
          Asking the Wayback Machine for its copy...
        {:else if capture}
          <a href={capture.url.replace(/^http:/, 'https:')} rel="nofollow noopener noreferrer">
            Wayback copy from {date(capture.timestamp)}
          </a>
        {:else}
          The Wayback Machine never archived it.
        {/if}
      </p>
    {/if}
    <p class="checked">
      {#if card.checked}Checked {date(card.checked)}.{/if}
      <a href={report}>Got it wrong?</a>
    </p>
  {:else}
    <p>A text post, so there's no link to check. {count(card.comments)} comments on HN.</p>
  {/if}
</article>

<style>
  .story {
    display: grid;
    gap: var(--space-2);
    overflow-wrap: anywhere;

    :is(h1, h2) {
      font-size: var(--size-l);
      outline: none;
    }
  }

  .meta,
  .link,
  .checked {
    color: var(--text-muted);
    font-size: var(--size-xs);

    a {
      text-decoration: underline;
    }
  }

  .link {
    user-select: all;
  }

  .archive a {
    text-decoration: underline;
    font-weight: bold;
  }
</style>
