import { describe, expect, it } from 'vitest';
import { destination, linkKey, shardOf } from '../src/lib/data.ts';

describe('shardOf', () => {
  it('picks the same host shard as the Python builder', () => {
    expect(shardOf('example.com')).toBe(697);
    expect(shardOf('github.com')).toBe(718);
    expect(shardOf('straße.de')).toBe(764);
    expect(shardOf('blog.codinghorror.com')).toBe(614);
  });

  it('shards story ids by number', () => {
    expect(shardOf(1234567)).toBe(1234567 % 1024);
  });
});

describe('linkKey', () => {
  it('ignores scheme, www, trailing slashes, index pages and tracking junk', () => {
    const plain = linkKey('http://example.com/posts/hello');
    expect(linkKey('https://www.example.com/posts/hello/')).toBe(plain);
    expect(linkKey('https://example.com/posts/hello/index.html')).toBe(plain);
    expect(linkKey('https://example.com/posts/hello?utm_source=hn&ref=x')).toBe(plain);
  });

  it('keeps a query that picks the page', () => {
    expect(linkKey('https://example.com/item?id=1')).not.toBe(
      linkKey('https://example.com/item?id=2')
    );
  });
});

describe('destination', () => {
  const story = { id: 1, url: 'https://example.com/a', day: '2010-01-02' };

  it('sends a link that still works to the page itself', () => {
    expect(destination({ ...story, fate: 'alive' })).toBe(story.url);
    expect(destination({ ...story, fate: 'moved', final: 'https://example.org/a' })).toBe(
      'https://example.org/a'
    );
  });

  it.each(['dead', 'elsewhere', 'unsure'] as const)(
    'never sends a %s link to the live page',
    (fate) => {
      expect(destination({ ...story, fate })).toBe(
        'https://web.archive.org/web/20100102/https://example.com/a'
      );
    }
  );

  it('sends a text post to its thread', () => {
    expect(destination({ id: 7, day: '2010-01-02' })).toBe(
      'https://news.ycombinator.com/item?id=7'
    );
  });
});
