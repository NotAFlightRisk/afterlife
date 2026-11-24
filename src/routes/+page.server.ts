import type { Graveyard } from '#lib/data.ts';

export const load = async ({ fetch }) => {
  const { hosts }: Graveyard = await (await fetch('/data/graveyard.json')).json();
  return { hosts: hosts.slice(0, 5) };
};
