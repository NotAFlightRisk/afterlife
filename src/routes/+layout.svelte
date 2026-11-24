<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';

  let { children } = $props();

  const links = [
    { href: '/', label: 'grid' },
    { href: '/day', label: 'this day' },
    { href: '/lookup', label: 'lookup' },
    { href: '/graveyard', label: 'graveyard' },
    { href: '/about', label: 'about' }
  ];
</script>

<div class="page">
  <header class="masthead">
    <a class="name" href="/">Hacker Afterlife</a>
    <nav aria-label="Main">
      {#each links as link (link)}
        <a href={link.href} aria-current={page.url.pathname === link.href ? 'page' : undefined}>
          {link.label}
        </a>
      {/each}
    </nav>
  </header>

  <main>
    {@render children()}
  </main>

  <footer>
    <p>
      Not part of Hacker News or Y Combinator, just a fan with a crawler. Stories come from
      <a href="https://hn.algolia.com/api">Algolia's HN API</a>, old copies from the
      <a href="https://web.archive.org/">Wayback Machine</a>.
    </p>
    <nav aria-label="More">
      <a href="/data/afterlife.csv.gz" download>the data (CSV)</a>
      <a href="/day.xml">RSS</a>
      <a href="https://github.com/NotAFlightRisk/afterlife">source</a>
      <a href="https://github.com/NotAFlightRisk/afterlife/issues/new?template=wrong_verdict.yml">
        wrong verdict?
      </a>
    </nav>
  </footer>
</div>

<style>
  .page {
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: var(--space-6);
    inline-size: min(var(--page), 100% - 2 * var(--gutter));
    min-block-size: 100dvh;
    margin-inline: auto;
    padding-block: var(--space-3) var(--space-8);
  }

  .masthead {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: var(--space-1) var(--space-4);
    padding-block-end: var(--space-2);
    border-block-end: 1px solid var(--rule);
  }

  .name {
    font-weight: bold;
  }

  nav {
    display: flex;
    flex-wrap: wrap;

    a:not(:first-child)::before {
      content: '|';
      content: '|' / '';
      display: inline-block;
      padding-inline: 0.4em;
      color: var(--text-muted);
    }

    [aria-current='page'] {
      font-weight: bold;
    }
  }

  footer {
    display: grid;
    gap: var(--space-2);
    padding-block-start: var(--space-3);
    border-block-start: 1px solid var(--rule);
    color: var(--text-muted);
    font-size: var(--size-xs);

    a {
      text-decoration: underline;
    }

    nav a {
      text-decoration: none;
    }
  }
</style>
