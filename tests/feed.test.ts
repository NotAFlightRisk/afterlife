import { describe, expect, it } from 'vitest';
import type { Card } from '../src/lib/data.ts';
import { feed } from '../src/lib/feed.ts';
import { yearsBefore } from '../src/lib/format.ts';

const story = (title: string, fate: Card['fate']): Card => ({
  id: 1,
  url: 'https://example.com/a?x=1&y=2',
  title,
  points: 200,
  comments: 3,
  day: '2016-11-24',
  fate
});

describe('feed', () => {
  it('has one item per day ten years back that has stories', async () => {
    const asked: string[] = [];
    const xml = await feed('2026-11-24', async (day) => {
      asked.push(day);
      return day === '2016-11-24'
        ? { stories: [story('One', 'alive'), story('Two', 'dead')] }
        : undefined;
    });
    expect(asked).toHaveLength(7);
    expect(asked[0]).toBe('2016-11-24');
    expect(xml.match(/<item>/g)).toHaveLength(1);
    expect(xml).toContain('<title>24 Nov 2016: 1 of 2 links still work</title>');
  });

  it('escapes titles twice over, once for the HTML and once for the XML', async () => {
    const xml = await feed('2026-11-24', async () => ({
      stories: [story('<script>alert(1)</script> & co', 'alive')]
    }));
    expect(xml).not.toContain('<script>');
    expect(xml).toContain('&#38;#60;script&#38;#62;');
  });
});

describe('yearsBefore', () => {
  it('lands 29 February on the 28th in a year without one', () => {
    expect(yearsBefore('2024-02-29', 5)).toBe('2019-02-28');
    expect(yearsBefore('2024-02-29', 4)).toBe('2020-02-29');
  });
});

describe('feed around a leap day', () => {
  it('gives 28 and 29 February one item between them in a year without a 29th', async () => {
    const xml = await feed('2028-03-01', async (day) => ({ stories: [story(day, 'alive')] }));
    expect(xml.match(/<guid[^>]*>[^<]*d=2018-02-28</g)).toHaveLength(1);
  });
});
