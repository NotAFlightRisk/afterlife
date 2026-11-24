import { destination, hostOf, type Card, type Day } from './data.ts';
import { LABELS, works } from './fates.ts';
import { date, yearsBefore } from './format.ts';

const SITE = 'https://afterlife.peng.ly';
const DAYS = 7;

const escape = (text: string) => text.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);

function item(day: string, then: string, stories: Card[]) {
  const linked = stories.filter((story) => story.url);
  const still = linked.filter((story) => works(story.fate)).length;
  const rows = stories.map((story) => {
    const fate = story.fate ? ` (${LABELS[story.fate]})` : '';
    const host = story.url ? ` ${hostOf(story.url)}` : '';
    return `<li><a href="${escape(destination(story))}">${escape(story.title)}</a>${escape(host + fate)}</li>`;
  });
  const link = `${SITE}/day?d=${then}`;
  return `  <item>
    <title>${escape(`${date(then)}: ${still} of ${linked.length} links still work`)}</title>
    <link>${link}</link>
    <guid isPermaLink="true">${link}</guid>
    <pubDate>${new Date(`${day}T00:00:00Z`).toUTCString()}</pubDate>
    <description>${escape(`<ol>${rows.join('')}</ol>`)}</description>
  </item>`;
}

/** The last week of "HN ten years ago today", from whichever day files exist */
export async function feed(today: string, load: (day: string) => Promise<Day | undefined>) {
  const days = Array.from({ length: DAYS }, (_, back) => {
    const day = new Date(Date.parse(`${today}T00:00:00Z`) - back * 86_400_000);
    return day.toISOString().slice(0, 10);
  });
  const items = await Promise.all(
    days.map(async (day) => {
      const then = yearsBefore(day, 10);
      const stories = (await load(then))?.stories;
      return stories?.length ? item(day, then, stories) : '';
    })
  );
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Hacker News, ten years ago today</title>
  <link>${SITE}/day</link>
  <description>Each day's top 30 Hacker News stories from ten years back, and which links still work.</description>
  <language>en-gb</language>
${items.filter(Boolean).join('\n')}
</channel>
</rss>
`;
}
