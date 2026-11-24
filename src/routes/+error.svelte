<script lang="ts">
  import { page } from '$app/state';
  import Lost from '#lib/components/Lost.svelte';
</script>

<Lost status={page.status} />
