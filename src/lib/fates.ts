export const FATES = ['alive', 'moved', 'dead', 'elsewhere', 'unsure'] as const;
export type Fate = (typeof FATES)[number];

export const LABELS: Record<Fate, string> = {
  alive: 'alive',
  moved: 'moved',
  dead: 'dead',
  elsewhere: 'lands elsewhere',
  unsure: "can't tell"
};

/** Alive and moved links still load the story */
export const works = (fate?: Fate) => fate === 'alive' || fate === 'moved';

const WALLS: Record<string, string> = {
  '401': 'wants a login before it shows anything',
  '402': 'wants paying before it shows a crawler anything',
  '403': 'turns crawlers like ours away',
  '429': 'said we were asking too often',
  '451': "won't show it, for legal reasons",
  '999': 'turns crawlers away, the way LinkedIn does'
};

const WORDS: Record<string, string> = {
  alive: 'Still there, at the same address.',
  moved: "It's moved, but it's still the story.",
  gone: "Doesn't answer any more.",
  '404': "The site says it's not there (a 404).",
  '410': "The site says it's gone for good (a 410).",
  home: 'It redirects to a home page or an index now, not the story.',
  unrelated: "It redirects to a page that isn't the story.",
  parked: 'It lands on a parking page.',
  noanswer: "It didn't answer when we looked. It gets a second try a week later.",
  stall: 'The site takes the connection and then never answers, which is how some bot walls work.',
  reset: 'The site hangs up on us, home page and all.',
  challenge: 'A bot check is in the way.',
  consent: 'A cookie consent page is in the way.',
  login: 'A sign-in page is in the way.',
  robots: "The site's robots.txt asks crawlers like ours not to look, so we didn't.",
  'robots-error': "We couldn't read the site's robots.txt, so we didn't look.",
  soft404: 'The page loads, but so does any made-up address on that site, so that proves nothing.',
  tls: 'Its security setup is too broken to connect to.',
  private: "It's private now.",
  badurl: "The link itself doesn't make sense.",
  badreply: "The server's reply was garbled.",
  loop: 'It redirects round in a loop.',
  'home-changed': 'The home page is something else now.'
};

/** What a check found, in words a person would use */
export function plainWords(evidence?: string): string {
  if (!evidence) return "We haven't checked it yet.";
  if (evidence.startsWith('wall-')) {
    return `The site ${WALLS[evidence.slice(5)] ?? 'turns crawlers like ours away'}.`;
  }
  if (evidence.startsWith('status-')) {
    return `The server answered with an error (${evidence.slice(7)}).`;
  }
  return WORDS[evidence] ?? 'Something went wrong when we checked it.';
}
