<script lang="ts">
  import { browser } from '$app/env';
  import { page } from '$app/state';
  import StoryCard from '#lib/components/StoryCard.svelte';
  import { hostOf, linkKey, loadCard, loadHost, type Card } from '#lib/data.ts';
  import { plural } from '#lib/format.ts';

  type Answer =
    | { cards: Card[] }
    | { missing: 'story' }
    | { missing: 'link'; host: string; others: number }
    | { missing: 'nonsense' };

  const BOOKMARKLET =
    "javascript:location.href='https://afterlife.peng.ly/lookup?q='+encodeURIComponent(location.href)";

  const query = $derived(browser ? (page.url.searchParams.get('q') ?? '').trim() : '');
  let answer = $state<Answer>();

  async function find(text: string): Promise<Answer> {
    const id = text.match(/[?&]id=(\d+)/)?.[1] ?? text.match(/^\d+$/)?.[0];
    if (id) {
      const card = await loadCard(Number(id));
      return card ? { cards: [card] } : { missing: 'story' };
    }
    const url = /^https?:\/\//i.test(text) ? text : `https://${text}`;
    const host = hostOf(url);
    if (!host.includes('.')) return { missing: 'nonsense' };
    const rows = await loadHost(host);
    const key = linkKey(url);
    const matches = rows.filter((row) => linkKey(row[5]) === key);
    if (!matches.length) return { missing: 'link', host, others: rows.length };
    const cards = await Promise.all(matches.map((row) => loadCard(row[0])));
    return { cards: cards.filter((card) => card !== undefined) };
  }

  $effect(() => {
    answer = undefined;
    if (query) find(query).then((found) => (answer = found));
  });
</script>

<svelte:head>
  <title>Look up a Hacker News link | Hacker Afterlife</title>
  <meta
    name="description"
    content="Paste a Hacker News thread or a link that made HN to see whether it still works, and get its Wayback copy if it doesn't."
  />
</svelte:head>

<div class="lookup">
  <h1>Look up a link</h1>
  <form method="GET" action="/lookup" role="search">
    <label for="q">An HN thread, or a link that made it onto HN</label>
    <div>
      <input
        id="q"
        name="q"
        type="text"
        inputmode="url"
        value={query}
        placeholder="https://news.ycombinator.com/item?id=1234567"
        required
      />
      <button type="submit">look it up</button>
    </div>
  </form>

  <div class="answer" aria-live="polite">
    {#if query && !answer}
      <p class="quiet">Looking...</p>
    {:else if answer && 'cards' in answer}
      {#each answer.cards as card (card)}
        <StoryCard {card} heading="h2" />
      {/each}
    {:else if answer?.missing === 'story'}
      <p>
        That story isn't one of ours. We only check stories that got 100 points or made their day's
        top 30, so it either didn't, or it's newer than our last crawl.
      </p>
    {:else if answer?.missing === 'link'}
      <p>
        That exact link never made the cut, and there's no live checker behind this page.
        {#if answer.others}
          {plural(answer.others, 'other story', 'other stories')} from {answer.host} did, though:
          <a href="/domain/{answer.host}">see how they're doing</a>.
        {/if}
      </p>
    {:else if answer?.missing === 'nonsense'}
      <p>That doesn't look like a link or an HN thread. Try pasting the whole address.</p>
    {/if}
  </div>

  <section class="bookmarklet" aria-labelledby="bookmarklet">
    <h2 id="bookmarklet">On a thread already?</h2>
    <p>
      Drag this to your bookmarks bar, then click it on any HN thread to see what became of its
      link:
      <a class="button" href={BOOKMARKLET}>afterlife this</a>
    </p>
  </section>
</div>

<style>
  .lookup,
  form,
  .answer,
  .bookmarklet {
    display: grid;
    gap: var(--space-3);
    max-inline-size: 44rem;
  }

  h1 {
    font-size: var(--size-l);
  }

  h2 {
    font-size: var(--size-m);
  }

  form {
    gap: var(--space-1);
    font-size: var(--size-s);

    div {
      display: flex;
      gap: var(--space-2);
    }

    input {
      flex: 1;
      min-inline-size: 0;
    }
  }

  .answer {
    gap: var(--space-6);

    a {
      text-decoration: underline;
    }
  }

  .bookmarklet {
    padding-block-start: var(--space-4);
    border-block-start: 1px solid var(--rule);
    color: var(--text-muted);
  }

  .button {
    display: inline-block;
    color: var(--text);
    cursor: grab;
  }

  .quiet {
    color: var(--text-muted);
  }
</style>
