<script lang="ts">
  import { LABELS, type Fate } from '#lib/fates.ts';

  let { fate }: { fate?: Fate } = $props();
</script>

{#if fate}
  <span class="fate {fate}">{LABELS[fate]}</span>
{/if}

<style>
  .fate {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    white-space: nowrap;

    &::before {
      content: '';
      inline-size: 0.7em;
      block-size: 0.7em;
      background: var(--chip);
      box-shadow: var(--chip-edge);
    }
  }

  .alive {
    --chip: var(--fate-alive);
  }

  .moved {
    --chip: var(--fate-moved);
  }

  .dead {
    --chip: var(--fate-dead);
    font-weight: bold;
  }

  .elsewhere {
    --chip: var(--fate-elsewhere);
  }

  .unsure {
    --chip: var(--hatch);
  }
</style>
