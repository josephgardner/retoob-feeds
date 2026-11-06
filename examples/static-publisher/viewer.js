/* One static viewer for the directory, feeds and individual cards. */
const site = new URL('.', document.currentScript.src);
const parameters = new URLSearchParams(location.search);
const content = document.getElementById('content');
function element(tag, text) { const node = document.createElement(tag); if (text) node.textContent = text; return node; }
function safeUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password) throw new Error('Unsupported link');
  return url.href;
}
function link(text, url) { const node = element('a', text); node.href = url; return node; }
function viewer(feed, item) {
  const url = new URL('index.html', site); url.searchParams.set('feed', feed);
  if (item) url.searchParams.set('item', item);
  return url.href;
}
async function json(url) {
  const response = await fetch(url, { credentials: 'omit', cache: 'no-cache', redirect: 'error' });
  if (!response.ok) throw new Error('This feed is currently unavailable.');
  const body = await response.text();
  if (body.length > 10 * 1024 * 1024) throw new Error('This feed exceeds the viewer limit.');
  return JSON.parse(body);
}
async function render() {
  const id = parameters.get('feed');
  if (!id) {
    const directory = await json(new URL('feeds.json', site));
    if (!Array.isArray(directory.feeds) || directory.feeds.length > 200) throw new Error('Invalid feed collection');
    document.getElementById('intro').textContent = 'Retoob includes these feeds automatically. You can also subscribe using the feed collection JSON link.';
    for (const feed of directory.feeds) {
      const url = new URL(safeUrl(feed.url));
      const feedId = url.pathname.split('/').at(-2);
      if (!/^[A-Za-z0-9_-]+$/.test(feedId)) continue;
      const card = element('article'); const heading = element('h2'); heading.append(link(feed.title || feedId, viewer(feedId)));
      card.append(heading, link('Feed JSON', url.href)); content.append(card);
    }
    return;
  }
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(id)) throw new Error('Invalid feed');
  const feedUrl = new URL(encodeURIComponent(id) + '/feed.json', site);
  const feed = await json(feedUrl);
  if (!Array.isArray(feed.items) || feed.items.length > 1000 || feed._retoob?.version !== 1) throw new Error('Invalid video feed');
  document.title = feed.title; document.getElementById('title').textContent = feed.title;
  document.getElementById('intro').textContent = feed.description || '';
  const subscription = document.getElementById('subscribe'); subscription.textContent = 'Feed JSON'; subscription.href = feedUrl.href;
  const selected = parameters.get('item');
  const items = selected ? feed.items.filter(item => item._retoob?.itemId === selected) : feed.items;
  if (selected && !items.length) throw new Error('This video is no longer in the current feed.');
  for (const item of items) {
    const card = element('article');
    if (item.image) {
      try { const image = element('img'); image.src = safeUrl(item.image); image.alt = ''; image.loading = 'lazy'; image.referrerPolicy = 'no-referrer'; card.append(image); } catch {}
    }
    const heading = element('h2'); heading.append(link(item.title, viewer(id, item._retoob.itemId))); card.append(heading);
    if (selected) card.append(element('p', item.content_text));
    const links = element('div'); links.className = 'links';
    try { links.append(link('Watch video', safeUrl(item.external_url))); } catch {}
    if (selected) links.append(link('All videos in this feed', viewer(id)));
    else links.append(link('Details & sources', viewer(id, item._retoob.itemId)));
    card.append(links); content.append(card);
  }
}
render().catch(error => { document.getElementById('intro').textContent = error.message; });
