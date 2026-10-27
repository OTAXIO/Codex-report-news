'use strict';
const story=JSON.parse(document.getElementById('story-data').textContent);
const sceneNodes=story.scenes.map(s=>document.getElementById('scene-'+s.id));
const caption=document.getElementById('caption');
const modules=document.getElementById('modules');
const chapters=document.getElementById('chapters');
const markers=document.getElementById('markers');
const moduleNodes=story.progress.modules.map(m=>{const n=document.createElement('div');n.className='module';n.textContent=m.label;n.style.left=(1728*m.start/story.duration)+'px';n.style.width=(1728*(m.end-m.start)/story.duration)+'px';modules.append(n);return n;});
const chapterNodes=story.progress.chapters.map((c,i)=>{const n=document.createElement('div');const b=story.progress.chapter_bounds[i];n.className='chapter';n.textContent=b.width<65?String(i).padStart(2,'0'):c.label;n.style.left=(b.x-96)+'px';n.style.width=b.width+'px';n.style.fontSize=Math.min(21,Math.max(16,b.width/Math.max(1,c.label.length)))+'px';chapters.append(n);if(i){const line=document.createElement('div');line.className='marker';line.style.left=b.x+'px';markers.append(line);}return n;});
function clock(t){const s=Math.floor(Math.max(0,t));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function render(t){
  const time=Math.max(0,Math.min(t,story.duration-1e-7));
  const current=story.scenes.findIndex(s=>time>=s.start&&time<s.end);
  sceneNodes.forEach((n,i)=>{const active=i===current;const p=Math.min(1,Math.max(0,(time-story.scenes[i].start)/.32));const ease=1-Math.pow(1-p,3);n.style.visibility=active?'visible':'hidden';n.style.opacity=active?String(ease):'0';n.style.transform='translateX('+((1-ease)*(story.template==='graphic'?48:20))+'px)';});
  const cue=story.captions.find(c=>time>=c.start&&time<c.end);caption.textContent=cue?cue.text:'';
  document.getElementById('now-label').textContent=current>=0?story.scenes[current].section+' / '+story.scenes[current].title:'';
  document.getElementById('clock').textContent=clock(time)+' / '+clock(story.duration);
  document.getElementById('fill').style.transform='scaleX('+(time/story.duration)+')';
  chapterNodes.forEach((n,i)=>{n.className=i===current?'chapter active':'chapter';});
  moduleNodes.forEach((n,i)=>{const m=story.progress.modules[i];n.className=time>=m.start&&time<m.end?'module active':'module';});
}
Shot.define({duration:story.duration,fps:30,cuts:story.scenes.slice(1).map(s=>s.start),
  fonts:[['700 64px NewsSans','新闻导览国内国际'],['400 29px NewsSans','来源北京时间']],
  setup:()=>Promise.all(Array.from(document.images,img=>img.decode())),
  render,post:{motionBlur:1,grain:0},meta:{template:story.template,chapters:story.progress.chapters}});
