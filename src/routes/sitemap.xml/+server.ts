export const prerender = true;

const SITE = 'https://afterlife.peng.ly';
const PAGES = ['/', '/day', '/lookup', '/graveyard', '/about'];

export const GET = () =>
  new Response(
    `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${PAGES.map((path) => `  <url><loc>${SITE}${path}</loc></url>`).join('\n')}
</urlset>
`,
    { headers: { 'Content-Type': 'application/xml' } }
  );
