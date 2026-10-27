// Read-only geometry checks against the same pinned runtime used for rendering.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {startServer} from '../node_modules/multiplane/src/server.mjs';
const require=createRequire(fs.realpathSync(new URL('../node_modules/multiplane/package.json',import.meta.url)));
const {chromium}=require('playwright');
const [shot,output]=process.argv.slice(2);
const server=await startServer(0,path.dirname(path.resolve(shot)));
let browser;
try{
  browser=await chromium.launch({headless:true,channel:'chromium'});
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
  await page.goto(server.url+'/'+path.basename(shot)+'?mode=render');
  await page.evaluate(()=>window.SHOT.ready);
  const data=await page.evaluate(()=>JSON.parse(document.getElementById('story-data').textContent));
  const times=[0,data.duration-1/30,...data.scenes.flatMap(s=>[Math.min(s.end-.01,s.start+.4),(s.start+s.end)/2]),...data.captions.map(c=>(c.start+c.end)/2)];
  const failures=[];
  for(const t of times){
    const findings=await page.evaluate(t=>{
      window.SHOT.render(t);
      const root=Array.from(document.querySelectorAll('.scene')).find(n=>n.style.visibility==='visible');
      if(!root)return ['missing_scene'];
      const facts=root.querySelector('.facts');const source=root.querySelector('.source');
      const title=root.querySelector('h1');const notes=[];
      if(facts&&title.getBoundingClientRect().bottom>facts.getBoundingClientRect().top-8)notes.push('headline_overlaps_facts');
      if(facts&&source&&facts.getBoundingClientRect().bottom>source.getBoundingClientRect().top-10)notes.push('facts_overlap_source');
      for(const n of root.querySelectorAll('h1,.facts,.overview-grid,.source,.brand,.photo,.route,.metrics,.identity')){
        const b=n.getBoundingClientRect();if(b.left<90||b.right>1840||b.top<95||b.bottom>821)notes.push('outside_reading_area:'+n.className);
      }
      const cap=document.getElementById('caption');if(cap.scrollWidth>cap.clientWidth+1)notes.push('caption_overflow');
      return notes;
    },t);
    if(findings.length)failures.push({time:t,findings});
  }
  const result={ok:failures.length===0,samples:times.length,failures};
  fs.writeFileSync(output,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  if(!result.ok)process.exitCode=1;
}finally{await browser?.close();await server.close();}
