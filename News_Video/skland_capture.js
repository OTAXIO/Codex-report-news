// Run in the Claude built-in browser on a Skland official list page
// (skland.com/game/<game>?cateId=N) or an article page (skland.com/article?id=N),
// after the page has rendered. It reads the item/user objects the page already
// rendered (React props) and returns them; it sends no request, reads no cookie
// and signs nothing. Save the returned JSON to data/skland-captures/ and run
// `python -B skland_sources.py import <file>`.
(() => {
  const HOURS = 72, LIMIT = 1500;
  // Legal/FAQ boilerplate carries no news facts and would bloat every capture.
  const BOILERPLATE = /\n(法律声明|【?活动提醒】?|【?信使公署提醒】?|活动FAQ|【特别说明】|作品要求|【奖品清单】)/;
  const cutoff = Date.now() / 1000 - HOURS * 3600;
  const pageId = new URL(location.href).searchParams.get('id');
  const textOf = item => {
    const parts = [];
    for (const c of item.caption || []) {
      const t = c.kind === 'link' ? (c.link && c.link.text) : (c.text && c.text.text);
      if (!t) continue;
      // Links sit inside a sentence; text nodes are paragraphs.
      if (c.kind === 'link' && parts.length) parts[parts.length - 1] += t;
      else if (parts.length && /[^。！？!?：:）)」』\]】~～…]$/.test(parts[parts.length - 1]) && c.kind === 'text' && !c.bold && /^[^\d#【「▼*]/.test(t)) parts[parts.length - 1] += t;
      else parts.push(t);
    }
    // Endfield posts end with a fixed "————————▼ current version" promo footer; it is not this post's news.
    return parts.join('\n').split(BOILERPLATE)[0].split('————————')[0].trim();
  };
  const rows = {};
  const consider = v => {
    if (!v || typeof v !== 'object' || !v.item || !v.user || !v.item.id || !v.item.publishedAtTs) return;
    if (v.user.identity !== 2) return; // official accounts only; the importer re-checks names
    const id = String(v.item.id);
    if (rows[id] || (pageId ? id !== pageId : Number(v.item.publishedAtTs) < cutoff)) return;
    const text = textOf(v.item);
    rows[id] = {
      item: {
        id, title: v.item.title, gameId: v.item.gameId, cateId: v.item.cateId,
        publishedAtTs: String(v.item.publishedAtTs),
        imageList: (v.item.imageList || []).map(i => ({ url: i.url })).slice(0, 6),
        text: text.slice(0, LIMIT), text_truncated: text.length > LIMIT,
      },
      user: { id: String(v.user.id), nickname: v.user.nickname, identity: v.user.identity },
    };
  };
  const nodes = pageId ? document.querySelectorAll('body *') : document.querySelectorAll('a[href*="/article?id="]');
  for (const node of nodes) {
    const key = Object.keys(node).find(k => k.startsWith('__reactFiber'));
    let fiber = key && node[key], depth = 0;
    while (fiber && depth++ < 60) {
      const props = fiber.memoizedProps;
      if (props && typeof props === 'object') for (const v of Object.values(props)) consider(v);
      fiber = fiber.return;
    }
    if (pageId && rows[pageId]) break;
  }
  return { page: location.href, captured_at: new Date().toISOString(), hours: HOURS, rows: Object.values(rows) };
})()
