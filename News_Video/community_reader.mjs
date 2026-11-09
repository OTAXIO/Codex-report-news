// Read-only B站 community reader for the 玩家热议 segment (2026-11-09 user decision).
//
// Uses a dedicated local Chrome profile that the user logged into once (a
// secondary account). It only reads what the rendered pages show: no cookie
// export, no direct comment/search API calls, no WBI signing, no replayed
// requests. Usernames, avatars and UIDs are never read.
//
//   node community_reader.mjs <job.json>
//   job: {mode: login|login-check|search|comments, profile_dir, browser_executable,
//         puppeteer_module, searches:[{label,url}], videos:[bvid], scrolls, interval_ms:[min,max]}
// Output: one JSON object on stdout {ok, ...} or {ok:false, error:{code,message}}.
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import * as dom from './community_dom.mjs';

const job=JSON.parse(fs.readFileSync(process.argv[2],'utf8').replace(/^﻿/,''));
const imported=job.puppeteer_module?await import(pathToFileURL(job.puppeteer_module).href):await import('puppeteer-core');
const puppeteer=imported.default;
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const between=()=>{const [a,b]=job.interval_ms||[3000,5000];return a+Math.random()*(b-a);};
const out=value=>{process.stdout.write(JSON.stringify(value));};
class Stop extends Error{constructor(code,message){super(message);this.code=code;}}

async function blocked(page){return page.evaluate(dom.isBlocked);}
async function loggedIn(page){
  await page.goto('https://www.bilibili.com/',{waitUntil:'domcontentloaded',timeout:45000});
  await pause(2500);
  return page.evaluate(dom.isLoggedIn);
}
async function readCards(page){return page.evaluate(dom.cards);}
async function readComments(page){return page.evaluate(dom.comments);}
async function headerInfo(page){return page.evaluate(dom.header);}
async function sortBy(page,label){return page.evaluate(dom.clickSort,label);}
async function quiet(page){await page.evaluate(()=>{const v=document.querySelector('video');if(v){v.muted=true;v.pause();}}).catch(()=>{});}

async function video(page,bvid){
  await page.goto('https://www.bilibili.com/video/'+bvid+'/',{waitUntil:'domcontentloaded',timeout:45000});
  await pause(2500);await quiet(page);
  if(await blocked(page))throw new Stop('PLATFORM_BLOCKED','Verification or risk page on a video');
  await page.evaluate(()=>document.querySelector('bili-comments')?.scrollIntoView());
  await pause(3500);
  const result={bvid,sorts:{}};
  for(const [sort,label] of [['hot','最热'],['newest','最新']]){
    if(sort==='newest'){if(!await sortBy(page,label)){result.sorts[sort]={error:'sort_button_missing',comments:[]};continue;}await pause(3000);}
    for(let i=0;i<(job.scrolls||5);i++){await page.evaluate(()=>window.scrollBy(0,2000));await pause(1800);await quiet(page);}
    if(await blocked(page))throw new Stop('PLATFORM_BLOCKED','Verification or risk page while reading comments');
    result.sorts[sort]={comments:await readComments(page)};
  }
  Object.assign(result,await headerInfo(page));
  return result;
}

let browser;
try{
  const headless=job.mode!=='login';
  browser=await puppeteer.launch({executablePath:job.browser_executable,userDataDir:job.profile_dir,headless,defaultViewport:{width:1440,height:1000},args:['--mute-audio','--no-first-run']});
  const page=(await browser.pages())[0]||await browser.newPage();
  if(job.mode==='login'){
    // The user logs in by themselves in this window; we only wait and check.
    await page.goto('https://passport.bilibili.com/login',{waitUntil:'domcontentloaded',timeout:45000});
    const end=Date.now()+(job.login_timeout_ms||600000);let ok=false;
    while(Date.now()<end){
      await pause(5000);
      ok=await page.evaluate(()=>!location.href.includes('passport.bilibili.com/login')).catch(()=>false);
      if(ok){ok=await loggedIn(page);break;}
    }
    out({ok,mode:'login'});
  }else if(job.mode==='login-check'){
    out({ok:true,mode:'login-check',logged_in:await loggedIn(page)});
  }else{
    if(!await loggedIn(page))throw new Stop('COMMUNITY_LOGIN_REQUIRED','The reader profile is not logged in to B站');
    if(job.mode==='search'){
      const searches=[];
      for(const [i,s] of (job.searches||[]).entries()){
        if(i)await pause(between());
        await page.goto(s.url,{waitUntil:'domcontentloaded',timeout:45000});await pause(3500);
        if(await blocked(page))throw new Stop('PLATFORM_BLOCKED','Verification or risk page on search');
        searches.push({label:s.label,url:page.url(),cards:await readCards(page)});
      }
      out({ok:true,mode:'search',searches});
    }else if(job.mode==='comments'){
      const videos=[];
      for(const [i,bvid] of (job.videos||[]).entries()){
        if(i)await pause(between());
        videos.push(await video(page,bvid));
      }
      out({ok:true,mode:'comments',videos});
    }else throw new Stop('BAD_INPUT','Unknown mode');
  }
}catch(error){
  out({ok:false,error:{code:error.code||'UPSTREAM_BROKEN',message:String(error.message||error).slice(0,300)}});
}finally{if(browser)await browser.close().catch(()=>{});}
