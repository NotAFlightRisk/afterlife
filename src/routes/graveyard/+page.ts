import type { Graveyard } from '#lib/data.ts';

const SHOWN = 200;

export const load = async ({ fetch }) => {
  const graveyard: Graveyard = await (await fetch('/data/graveyard.json')).json();
  return {
    upvoted: graveyard.upvoted.slice(0, SHOWN),
    hosts: graveyard.hosts.slice(0, SHOWN),
    launches: graveyard.show_hn.slice(0, SHOWN)
  };
};
