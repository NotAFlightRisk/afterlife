import type { Stats } from '#lib/data.ts';

export const prerender = true;

export const load = async ({ fetch }) => ({
  stats: (await (await fetch('/data/stats.json')).json()) as Stats
});
