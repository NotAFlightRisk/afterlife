import type { Day } from '../src/lib/data.ts';
import { feed } from '../src/lib/feed.ts';

interface Env {
  ASSETS: { fetch: (request: Request | URL) => Promise<Response> };
}

export default {
  async fetch(request: Request, env: Env) {
    const url = new URL(request.url);
    if (url.pathname !== '/day.xml') return env.ASSETS.fetch(request);
    const load = async (day: string) => {
      const file = await env.ASSETS.fetch(new URL(`/data/day/${day}.json`, url));
      return file.ok ? ((await file.json()) as Day) : undefined;
    };
    const today = new Date().toISOString().slice(0, 10);
    return new Response(await feed(today, load), {
      headers: {
        'Content-Type': 'application/rss+xml; charset=utf-8',
        'Cache-Control': 'public, max-age=3600'
      }
    });
  }
};
