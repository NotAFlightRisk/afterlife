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

<svelte:head>
  <meta property="og:image" content="https://afterlife.peng.ly/og.png" />
  <meta name="twitter:card" content="summary_large_image" />
</svelte:head>

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
    <a class="button github" href="https://github.com/NotAFlightRisk/afterlife">
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path
          d="M6.766 11.328c-2.063-.25-3.516-1.734-3.516-3.656 0-.781.281-1.625.75-2.188-.203-.515-.172-1.609.063-2.062.625-.078 1.468.25 1.968.703.594-.187 1.219-.281 1.985-.281.765 0 1.39.094 1.953.265.484-.437 1.344-.765 1.969-.687.218.422.25 1.515.046 2.047.5.593.766 1.39.766 2.203 0 1.922-1.453 3.375-3.547 3.64.531.344.89 1.094.89 1.954v1.625c0 .468.391.734.86.547C13.781 14.359 16 11.53 16 8.03 16 3.61 12.406 0 7.984 0 3.563 0 0 3.61 0 8.031a7.88 7.88 0 0 0 5.172 7.422c.422.156.828-.125.828-.547v-1.25c-.219.094-.5.156-.75.156-1.031 0-1.64-.562-2.078-1.609-.172-.422-.36-.672-.719-.719-.187-.015-.25-.093-.25-.187 0-.188.313-.328.625-.328.453 0 .844.281 1.25.86.313.452.64.655 1.031.655s.641-.14 1-.5c.266-.265.47-.5.657-.656"
        />
      </svg>
      GitHub
    </a>
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
    display: grid;
    grid-template: 'name nav github' / auto 1fr auto;
    align-items: baseline;
    gap: var(--space-1) var(--space-4);
    padding-block-end: var(--space-2);
    border-block-end: 1px solid var(--rule);

    /* too narrow for one line, so the button stays up by the name and the links go below */
    @media (width < 40rem) {
      grid-template: 'name github' 'nav nav' / 1fr auto;
    }
  }

  .name {
    grid-area: name;
    font-weight: bold;
  }

  .masthead nav {
    grid-area: nav;
  }

  .github {
    grid-area: github;
    white-space: nowrap;

    svg {
      inline-size: 1em;
      block-size: 1em;
      vertical-align: -0.125em;
      fill: currentColor;
    }
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
