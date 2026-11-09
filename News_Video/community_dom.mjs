// Page-side readers for community_reader.mjs; pure functions run inside page.evaluate,
// exported separately so tests can run them on a local fixture page.
export function isBlocked(){
  const text=document.body?document.body.innerText.slice(0,4000):'';
  return Boolean(document.querySelector('.geetest_panel, .geetest_holder, iframe[src*="captcha"], .bili-mini-mask .verify'))
    || /验证码|安全验证|访问异常|账号异常|操作频繁|risk control/i.test(text) || /passport\.bilibili\.com\/.*(verify|risk)/.test(location.href);
}
// Logged-in headers render the account avatar image; the logged-out header shows a 登录 button instead.
export function isLoggedIn(){return Boolean(document.querySelector('.header-avatar-wrap img'));}
export function cards(){
  return [...document.querySelectorAll('.bili-video-card')].map(c=>({
    title:(c.querySelector('.bili-video-card__info--tit')?.getAttribute('title')||c.querySelector('.bili-video-card__info--tit')?.textContent||'').trim(),
    bvid:((c.querySelector('a[href*="/video/"]')?.getAttribute('href')||'').match(/BV\w+/)||[])[0]||null,
    stats:[...c.querySelectorAll('.bili-video-card__stats--item')].map(s=>s.textContent.trim()),
    date:(c.querySelector('.bili-video-card__info--date')?.textContent||'').replace(/^[\s·]+/,'').trim()
  })).filter(c=>c.bvid);
}
// Comment text and like count only; author names, avatars and UIDs are never read.
export function comments(){
  const sr=document.querySelector('bili-comments')?.shadowRoot;if(!sr)return [];
  return [...sr.querySelectorAll('bili-comment-thread-renderer')].map(t=>{
    const rs=t.shadowRoot?.querySelector('#comment')?.shadowRoot;
    const text=(rs?.querySelector('bili-rich-text')?.shadowRoot?.querySelector('#contents')?.textContent||'').trim();
    const likes=(rs?.querySelector('bili-comment-action-buttons-renderer')?.shadowRoot?.querySelector('#like')?.textContent||'').trim();
    return {text,likes};
  }).filter(c=>c.text);
}
export function header(){
  const hdr=document.querySelector('bili-comments')?.shadowRoot?.querySelector('bili-comments-header-renderer')?.shadowRoot;
  return {header:(hdr?.textContent||'').replace(/\s+/g,' ').trim(),title:document.title};
}
export function clickSort(label){
  const hdr=document.querySelector('bili-comments')?.shadowRoot?.querySelector('bili-comments-header-renderer')?.shadowRoot;
  const button=hdr&&[...hdr.querySelectorAll('*')].find(e=>e.textContent.trim()===label&&!e.children.length);
  if(!button)return false;button.click();return true;
}
