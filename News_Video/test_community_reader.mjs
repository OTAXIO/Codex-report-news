// Offline check of the B站 page readers on a local shadow-DOM fixture.
//   node test_community_reader.mjs <puppeteer_module> <chrome_executable>
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import * as dom from './community_dom.mjs';

const [modulePath,chrome]=process.argv.slice(2);
const puppeteer=(await import(pathToFileURL(modulePath).href)).default;

const fixture=({loggedIn=true,blocked=false}={})=>`<!doctype html><meta charset="utf-8"><title>fixture</title>
<div class="header-avatar-wrap">${loggedIn?'<img src="data:,">':'<button>登录</button>'}</div>
${blocked?'<div>请完成安全验证</div>':''}
<div class="bili-video-card"><a href="/video/BV1GGWb6cEe6/"></a><h3 class="bili-video-card__info--tit" title="明河：我已悟出最强一剑">x</h3>
<span class="bili-video-card__stats--item">9126</span><span class="bili-video-card__stats--item">31</span><span class="bili-video-card__info--date">· 40分钟前</span></div>
<bili-comments></bili-comments>
<script>
const shadow=(tag,html)=>{const e=document.createElement(tag);e.attachShadow({mode:'open'}).innerHTML=html;return e;};
const host=document.querySelector('bili-comments');const root=host.attachShadow({mode:'open'});
root.appendChild(shadow('bili-comments-header-renderer','<span>评论 2</span><span>最热</span><span id="newest">最新</span>'));
root.querySelector('bili-comments-header-renderer').shadowRoot.getElementById('newest').onclick=()=>{window.__sorted='newest';};
for(const [text,like] of [['明河这把剑太帅了','112'],['活动奖励还挺多','9']]){
  const thread=document.createElement('bili-comment-thread-renderer');const ts=thread.attachShadow({mode:'open'});
  const comment=document.createElement('bili-comment-renderer');comment.id='comment';const cs=comment.attachShadow({mode:'open'});
  cs.innerHTML='<div id="user-name">某位用户</div>';
  cs.appendChild(shadow('bili-rich-text','<p id="contents">'+text+'</p>'));
  cs.appendChild(shadow('bili-comment-action-buttons-renderer','<span id="like">'+like+'</span>'));
  ts.appendChild(comment);root.appendChild(thread);
}
</script>`;

const browser=await puppeteer.launch({executablePath:chrome,headless:true,args:['--no-first-run']});
try{
  const page=await browser.newPage();
  await page.setContent(fixture());
  assert.equal(await page.evaluate(dom.isLoggedIn),true);
  assert.equal(await page.evaluate(dom.isBlocked),false);
  const comments=await page.evaluate(dom.comments);
  assert.deepEqual(comments,[{text:'明河这把剑太帅了',likes:'112'},{text:'活动奖励还挺多',likes:'9'}]);
  assert.ok(!JSON.stringify(comments).includes('某位用户'),'usernames are never read');
  assert.deepEqual(await page.evaluate(dom.cards),[{title:'明河：我已悟出最强一剑',bvid:'BV1GGWb6cEe6',stats:['9126','31'],date:'40分钟前'}]);
  assert.equal(await page.evaluate(dom.clickSort,'最新'),true);
  assert.equal(await page.evaluate(()=>window.__sorted),'newest');
  await page.setContent(fixture({loggedIn:false}));
  assert.equal(await page.evaluate(dom.isLoggedIn),false);
  await page.setContent(fixture({blocked:true}));
  assert.equal(await page.evaluate(dom.isBlocked),true);
  console.log('community reader fixture: ok');
}finally{await browser.close();}
