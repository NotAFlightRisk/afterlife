<script lang="ts">
  import Lost from '#lib/components/Lost.svelte';
</script>

<!-- prerendered as 404.html, which Cloudflare serves for any missing page -->
<Lost status={404} />
