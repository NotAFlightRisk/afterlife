<script lang="ts">
  import { getJson, type Dot } from '#lib/data.ts';
  import { FATES, LABELS, type Fate } from '#lib/fates.ts';
  import { count, percent } from '#lib/format.ts';

  interface Props {
    year: string;
    counts: Record<Fate, number>;
    months: number[];
    onhover: (dot: Dot | undefined, x: number, y: number) => void;
    onpick: (id: number) => void;
  }

  let { year, counts, months: sizes, onhover, onpick }: Props = $props();

  // keep in step with --month-gap, which lines the month names up over the columns
  const GAP = 6;
  // dead at the bottom of each month, then the murkier fates, then the ones that still work
  const STACK = [4, 3, 0, 1, 2];
  const CAPTURES: Record<number, number> = { 404: 0, 410: 0, 200: 2 };

  let box = $state<HTMLElement>();
  let canvas = $state<HTMLCanvasElement>();
  let dots = $state<Dot[]>();
  let width = $state(0);

  const total = $derived(Object.values(counts).reduce((sum, n) => sum + n, 0));
  const label = $derived(
    `${year}: ${count(total)} links. ` +
      FATES.map((fate) => `${count(counts[fate])} ${LABELS[fate]}`).join(', ') +
      '.'
  );

  const stacks = $derived.by(() => {
    const months: Dot[][] = sizes.map(() => []);
    for (const dot of dots ?? []) months[+dot[1].slice(5, 7) - 1].push(dot);
    const depth = (dot: Dot) =>
      STACK[dot[3]] * 3 + (dot[3] === 4 ? (CAPTURES[dot[5] ?? 0] ?? 1) : 0);
    for (const month of months) month.sort((a, b) => depth(a) - depth(b) || a[0] - b[0]);
    return months;
  });

  const layout = $derived.by(() => {
    // a desktop-ish guess until the browser measures, so the page starts close to its real size
    const span = width || 960;
    const pitch = span >= 640 ? 3 : 2;
    const column = (span - GAP * 11) / 12;
    const across = Math.max(1, Math.floor(column / pitch));
    const height = Math.max(...sizes.map((size) => Math.ceil(size / across)), 1) * pitch;
    return { pitch, column, across, height };
  });

  function hatch(context: CanvasRenderingContext2D, colour: string, ratio: number) {
    const tile = document.createElement('canvas');
    tile.width = tile.height = Math.max(3, Math.round(3 * ratio));
    const pen = tile.getContext('2d')!;
    pen.strokeStyle = colour;
    pen.lineWidth = Math.max(1, ratio * 0.75);
    pen.beginPath();
    pen.moveTo(0, tile.height);
    pen.lineTo(tile.width, 0);
    pen.stroke();
    const pattern = context.createPattern(tile, 'repeat')!;
    pattern.setTransform(new DOMMatrix().scale(1 / ratio));
    return pattern;
  }

  $effect(() => {
    if (!canvas || !width) return;
    const { pitch, column, across, height } = layout;
    const ratio = devicePixelRatio || 1;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const context = canvas.getContext('2d')!;
    context.scale(ratio, ratio);
    const style = getComputedStyle(canvas);
    const ground = style.getPropertyValue('--surface-sunk');
    if (!dots) {
      // each month's outline from the counts we already have, until its dots turn up
      context.fillStyle = ground;
      sizes.forEach((count, month) => {
        const tall = Math.ceil(count / across) * pitch;
        context.fillRect(month * (column + GAP), height - tall, across * pitch, tall);
      });
      return;
    }
    const colours = FATES.map((fate) => style.getPropertyValue(`--fate-${fate}`));
    // a can't-tell dot hatches in what Wayback last found there
    const [there, gone, unknown] = [0, 2, 4].map((fate) => hatch(context, colours[fate], ratio));
    const size = pitch - (pitch > 2 ? 1 : 0.5);
    stacks.forEach((stack, month) => {
      stack.forEach((dot, place) => {
        const x = month * (column + GAP) + (place % across) * pitch;
        const y = height - (Math.floor(place / across) + 1) * pitch;
        if (dot[3] === 4) {
          context.fillStyle = ground;
          context.fillRect(x, y, size, size);
          context.fillStyle = dot[5] === 200 ? there : dot[5] ? gone : unknown;
        } else {
          context.fillStyle = colours[dot[3]];
        }
        context.fillRect(x, y, size, size);
      });
    });
  });

  $effect(() => {
    const row = box;
    if (!row) return;
    let retry: ReturnType<typeof setTimeout>;
    const watch = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        watch.disconnect();
        getJson<Dot[]>(`/data/grid/${year}.json`)
          .then((found) => (dots = found ?? []))
          // a dropped connection gets another go once things calm down
          .catch(() => (retry = setTimeout(() => watch.observe(row), 5000)));
      },
      { rootMargin: '800px 0px' }
    );
    watch.observe(row);
    return () => {
      clearTimeout(retry);
      watch.disconnect();
    };
  });

  function dotAt(event: PointerEvent | MouseEvent) {
    const { pitch, column, across, height } = layout;
    const area = canvas!.getBoundingClientRect();
    const x = event.clientX - area.left;
    // a click in the gap between two months goes to whichever is nearer
    const month = Math.floor((x + GAP / 2) / (column + GAP));
    const into = Math.floor((x - month * (column + GAP)) / pitch);
    const along = Math.max(0, Math.min(into, across - 1));
    const up = Math.ceil((height - (event.clientY - area.top)) / pitch) - 1;
    if (month < 0 || month > 11 || up < 0) return;
    return stacks[month][up * across + along];
  }

  function randomDead() {
    const dead = dots?.filter((dot) => dot[3] === 2) ?? [];
    if (dead.length) onpick(dead[Math.floor(Math.random() * dead.length)][0]);
  }
</script>

<section class="year" bind:this={box} aria-labelledby="year-{year}">
  <header>
    <h3 id="year-{year}">{year}</h3>
    <p>{percent(counts.dead, total)} dead</p>
    <button type="button" onclick={randomDead} disabled={!dots}>a dead one</button>
  </header>
  <div
    class="plot"
    role="img"
    aria-label={label}
    bind:clientWidth={width}
    style:block-size="{layout.height}px"
  >
    <canvas
      bind:this={canvas}
      aria-hidden="true"
      style:inline-size="{width}px"
      style:block-size="{layout.height}px"
      onpointermove={(event) => onhover(dotAt(event), event.clientX, event.clientY)}
      onpointerleave={(event) => onhover(undefined, event.clientX, event.clientY)}
      onclick={(event) => {
        const dot = dotAt(event);
        if (dot) onpick(dot[0]);
      }}
    ></canvas>
  </div>
</section>

<style>
  .year {
    display: grid;
    grid-template-columns: var(--label, 6rem) 1fr;
    align-items: end;
    gap: var(--space-2) var(--space-4);
  }

  header {
    display: grid;
    gap: 0.1rem;
    font-size: var(--size-xs);
    color: var(--text-muted);

    h3 {
      font-size: var(--size-m);
      color: var(--text);
    }
  }

  button {
    justify-self: start;
    padding: 0;
    border: 0;
    background: none;
    text-decoration: underline;
    text-underline-offset: 0.15em;
    cursor: pointer;

    &:disabled {
      visibility: hidden;
    }
  }

  canvas {
    display: block;
    cursor: crosshair;
  }

  @media (max-width: 40rem) {
    .year {
      grid-template-columns: 1fr;
    }

    header {
      grid-auto-flow: column;
      justify-content: start;
      align-items: baseline;
      gap: var(--space-3);
    }
  }
</style>
