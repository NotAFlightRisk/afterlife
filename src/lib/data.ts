import { FATES, type Fate } from './fates.ts';

/** id, day, points, fate (an index into FATES), title, and a walled link's last good capture */
export type Dot = [number, string, number, number, string, number?];
/** id, day, points, fate, title and the link itself */
export type Row = [number, string, number, number, string, string];

export interface Card {
  id: number;
  url?: string;
  title: string;
  points: number;
  comments: number;
  day: string;
  fate?: Fate;
  evidence?: string;
  status?: number;
  final?: string;
  now?: string;
  checked?: string;
  captured?: string;
  captured_status?: number;
  was?: string;
  then?: string;
}

export interface Stats {
  years: Record<string, Record<Fate, number>>;
  months: Record<string, number>;
  checked: string;
  days: [string, string];
}

/** A day's stories, in HN's own order when we have its front page, else by points */
export interface Day {
  stories: Card[];
  front?: true;
}

export interface Graveyard {
  upvoted: Row[];
  hosts: { host: string; dead: number; elsewhere: number; stories: number }[];
  show_hn: Row[];
}

const SHARDS = 1024;
const TRACKING = /^(utm_\w+|ref|source|fbclid|gclid|mc_\w+)$/;
const TABLE = Array.from({ length: 256 }, (_, byte) => {
  let crc = byte;
  for (let bit = 0; bit < 8; bit++) crc = crc & 1 ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  return crc >>> 0;
});

/** zlib's crc32, so the browser picks the same shard the builder wrote */
export function crc32(text: string) {
  let crc = 0xffffffff;
  for (const byte of new TextEncoder().encode(text)) crc = TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

export const shardOf = (key: string | number) =>
  (typeof key === 'number' ? key : crc32(key)) % SHARDS;

export function hostOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

/** Scheme, www, trailing slashes, index pages and tracking junk don't make a link different */
export function linkKey(url: string) {
  const link = new URL(url);
  const path = link.pathname.split(';')[0].replace(/\/(index\.(html?|php))?$/, '');
  const query = [...link.searchParams]
    .filter(([key]) => !TRACKING.test(key))
    .map(([key, value]) => `${key}=${value}`)
    .sort()
    .join('&');
  return hostOf(url) + path.toLowerCase() + (query ? `?${query}` : '');
}

export const fateOf = (index: number): Fate => FATES[index];
export const thread = (id: number) => `https://news.ycombinator.com/item?id=${id}`;
export const wayback = (url: string, day: string) =>
  `https://web.archive.org/web/${day.replaceAll('-', '')}/${url}`;

/** Where a story's link should go: the page itself while it works, the archive once it doesn't */
export function destination(story: {
  id: number;
  url?: string;
  day: string;
  fate?: Fate;
  final?: string;
}) {
  if (!story.url) return thread(story.id);
  if (story.fate === 'alive') return story.url;
  if (story.fate === 'moved') return story.final ?? story.url;
  return wayback(story.url, story.day);
}

const loaded = new Map<string, Promise<unknown>>();

/** One request per file however many components ask, and a failed one can be asked again */
export function getJson<T>(path: string): Promise<T | undefined> {
  let file = loaded.get(path);
  if (!file) {
    file = fetch(path).then((reply) => (reply.ok ? reply.json() : undefined));
    file.catch(() => loaded.delete(path));
    loaded.set(path, file);
  }
  return file as Promise<T | undefined>;
}

export const loadCard = (id: number) =>
  getJson<Record<string, Card>>(`/data/id/${shardOf(id)}.json`).then((cards) => cards?.[id]);

export const loadHost = (host: string) =>
  getJson<Record<string, Row[]>>(`/data/host/${shardOf(host)}.json`).then(
    (hosts) => hosts?.[host] ?? []
  );

export const loadDay = (day: string) => getJson<Day>(`/data/day/${day}.json`);
