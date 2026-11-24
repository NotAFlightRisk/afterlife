<script lang="ts">
  let { status }: { status: number } = $props();
</script>

<svelte:head>
  <title>{status === 404 ? 'Not found' : 'Something broke'} | Hacker Afterlife</title>
</svelte:head>

<div class="lost">
  <h1>{status === 404 ? "There's nothing here" : 'Something broke'}</h1>
  <p>
    {status === 404
      ? 'Like a lot of old links, really.'
      : "That's on us, not you. Have another go in a minute."}
    <a href="/">Back to the grid</a>.
  </p>
</div>

<style>
  .lost {
    display: grid;
    gap: var(--space-2);

    h1 {
      font-size: var(--size-l);
    }

    a {
      text-decoration: underline;
    }
  }
</style>
