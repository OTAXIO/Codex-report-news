'use strict';
const story=JSON.parse(document.getElementById('story-data').textContent);
const sceneNodes=story.scenes.map(s=>document.getElementById('scene-'+s.id));
const caption=document.getElementById('caption');
const modules=document.getElementById('modules');
const chapters=document.getElementById('chapters');
const markers=document.getElementById('markers');
const wipe=document.getElementById('wipe');
const persona=story.template==='persona';
// Persona kicker: the category and its scope ("游戏资讯 / 明日方舟…") become two separate slanted tags.
if(persona)document.querySelectorAll('.kicker span').forEach(n=>{
  const [head,...rest]=n.textContent.split(' / ');
  n.textContent='';
  const b=document.createElement('b');b.className='rn';b.textContent=head;n.append(b);
  if(rest.length){const tail=document.createElement('em');tail.textContent=rest.join(' / ');n.append(tail);}
});
// The slab crosses each cut within ±0.25s and holds full cover around it, so the
// hard cut is hidden; stable reading frames from cut+0.25s onward are untouched.
const cuts=story.scenes.slice(1).map(s=>s.start);
function wipeAt(time){
  const c=cuts.find(c=>Math.abs(time-c)<.25);
  if(c===undefined)return null;
  const k=(time-c+.25)/.5;
  return Math.round(k<.4?-3100+2800*(k/.4):k<.6?-300:-300+2800*((k-.6)/.4));
}
const moduleNodes=story.progress.modules.map(m=>{const n=document.createElement('div');n.className='module';n.textContent=m.label;n.style.left=(1728*m.start/story.duration)+'px';n.style.width=(1728*(m.end-m.start)/story.duration)+'px';modules.append(n);return n;});
const chapterNodes=story.progress.chapters.map((c,i)=>{const n=document.createElement('div');const b=story.progress.chapter_bounds[i];n.className='chapter';n.textContent=b.width<65?String(i).padStart(2,'0'):c.label;n.style.left=(b.x-96)+'px';n.style.width=b.width+'px';n.style.fontSize=Math.min(21,Math.max(16,b.width/Math.max(1,c.label.length)))+'px';chapters.append(n);if(i){const line=document.createElement('div');line.className='marker';line.style.left=b.x+'px';markers.append(line);}return n;});
function clock(t){const s=Math.floor(Math.max(0,t));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function normKey(v){return String(v||'').replace(/[\s「」【】\[\]《》<>·•：:，,。.!！？?\-—_#()（）]/g,'').toLowerCase();}
function matchScore(sentNorm,label){
  const t=normKey(label);if(!sentNorm||t.length<2)return 0;
  if(sentNorm.includes(t))return t.length+4;
  let hits=0;
  for(let i=0;i<=t.length-2;i+=2){if(sentNorm.includes(t.slice(i,i+2)))hits++;}
  return hits>=2?hits:0;
}
function activeSentenceInfo(scene,time){
  const list=scene.sentences||[];
  if(!list.length)return {idx:0,text:''};
  let idx=0;
  for(let i=0;i<list.length;i++){if(time>=list[i].start)idx=i;}
  return {idx,text:list[idx].text||''};
}
function applyFocus(node,scene,time){
  const dur=Math.max(0.01,scene.end-scene.start);
  const prog=Math.min(0.9999,Math.max(0,(time-scene.start)/dur));
  const sent=activeSentenceInfo(scene,time);
  const sentNorm=normKey(sent.text);
  // Multi-image mid-scene switch (only 1 img displayed at any timestamp, preserving layout box).
  const multi=node.querySelector('.photo[data-multi="2"]');
  if(multi){
    const imgs=multi.querySelectorAll('img.photo-img');
    if(imgs.length>=2){
      const second=dur>=8&&time>=(scene.start+scene.end)/2;
      imgs[0].style.display=second?'none':'block';
      imgs[1].style.display=second?'block':'none';
    }
  }
  // 00 Overview cards: sequential highlight across the opening hook.
  const ovCards=Array.from(node.querySelectorAll('.overview-grid article'));
  if(ovCards.length>=2){
    const activeIdx=Math.min(ovCards.length-1,Math.floor(prog*ovCards.length));
    ovCards.forEach((el,i)=>{el.classList.toggle('is-active',i===activeIdx);el.classList.toggle('is-dim',i!==activeIdx);});
  }
  // Activity calendar rows: highlight rows named in the current spoken sentence, else scan smoothly.
  const calRows=Array.from(node.querySelectorAll('.cal-row'));
  if(calRows.length>=2){
    const matched=new Set();
    calRows.forEach((el,i)=>{if(matchScore(sentNorm,el.dataset.title||'')>=2)matched.add(i);});
    if(!matched.size)matched.add(Math.min(calRows.length-1,Math.floor(prog*calRows.length)));
    calRows.forEach((el,i)=>{const on=matched.has(i);el.classList.toggle('is-active',on);el.classList.toggle('is-dim',!on);});
  }
  // Body facts: audio-cue highlight matching current sentence or proportional progress.
  const facts=Array.from(node.querySelectorAll('.facts article'));
  if(facts.length>=2){
    let bestIdx=-1,bestScore=0;
    facts.forEach((el,i)=>{
      const heading=el.querySelector('h2')?.textContent||'';
      const detail=el.querySelector('p')?.textContent||'';
      const sc=matchScore(sentNorm,heading)*2+matchScore(sentNorm,detail);
      if(sc>bestScore){bestScore=sc;bestIdx=i;}
    });
    const activeIdx=bestScore>=3?bestIdx:Math.min(facts.length-1,Math.floor(prog*facts.length));
    facts.forEach((el,i)=>{el.classList.toggle('is-active',i===activeIdx);el.classList.toggle('is-dim',i!==activeIdx);});
  }
}
function render(t){
  const time=Math.max(0,Math.min(t,story.duration-1e-7));
  const current=story.scenes.findIndex(s=>time>=s.start&&time<s.end);
  sceneNodes.forEach((n,i)=>{const active=i===current;const p=Math.min(1,Math.max(0,(time-story.scenes[i].start)/.32));const ease=1-Math.pow(1-p,3);n.style.visibility=active?'visible':'hidden';n.style.opacity=active?String(ease):'0';const shift=(1-ease)*(persona?64:story.template==='graphic'?48:20);
    // Persona snaps its larger entry slide to whole pixels; fractional offsets rasterized differently across runs.
    n.style.transform='translateX('+(persona?Math.round(shift):shift)+'px)';
    if(active)applyFocus(n,story.scenes[i],time);});
  if(persona){const x=wipeAt(time);wipe.style.visibility=x===null?'hidden':'visible';wipe.style.transform='translateX('+(x===null?-3100:x)+'px) skewX(-18deg)';}
  const cue=story.captions.find(c=>time>=c.start&&time<c.end);caption.textContent=cue?cue.text:'';
  document.getElementById('now-label').textContent=current>=0?story.scenes[current].section+' / '+story.scenes[current].title:'';
  document.getElementById('clock').textContent=clock(time)+' / '+clock(story.duration);
  document.getElementById('fill').style.transform='scaleX('+(time/story.duration)+')';
  chapterNodes.forEach((n,i)=>{n.className=i===current?'chapter active':'chapter';});
  moduleNodes.forEach((n,i)=>{const m=story.progress.modules[i];n.className=time>=m.start&&time<m.end?'module active':'module';});
}
// Fact type grows to use the page: the largest step that still clears the source line, then spare
// height becomes breathing room. Measured once after fonts and images, in layout pixels.
function fitFacts(){
  document.querySelectorAll('.scene.fit').forEach(scene=>{
    const facts=scene.querySelector('.facts'),source=scene.querySelector('.source');
    if(!facts||!facts.children.length)return;
    const limit=(source?source.offsetTop:story.progress.reading_area_bottom)-14;
    const bottom=()=>facts.offsetTop+facts.offsetHeight;
    const steps=[1.4,1.32,1.24,1.16,1.08,1,.93];
    const step=steps.find(s=>{scene.style.setProperty('--fs',s);return bottom()<=limit;})||steps[steps.length-1];
    scene.style.setProperty('--fs',step);
    const n=facts.children.length;
    scene.style.setProperty('--air',Math.max(0,Math.min(20,Math.floor((limit-bottom())/(3*n-1))))+'px');
  });
}
Shot.define({duration:story.duration,fps:30,cuts:story.scenes.slice(1).map(s=>s.start),
  fonts:[['700 64px NewsSans','新闻导览国内国际'],['400 29px NewsSans','来源北京时间'],...(persona?[['400 168px PersonaDisplay','0123456789']]:[])],
  setup:()=>Promise.all(Array.from(document.images,img=>img.decode().catch(()=>{}))).then(fitFacts),
  render,post:{motionBlur:1,grain:0},meta:{template:story.template,chapters:story.progress.chapters}});
