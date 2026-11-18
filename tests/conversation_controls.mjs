import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../app/static/tutor-conversation.js', import.meta.url), 'utf8');
const settle = async () => { for (let i=0;i<12;i++) await Promise.resolve(); };
function harness() {
  let now=0, level=0, id=0, stopped=0;
  const frames=new Map(), spoken=[], requests=[];
  class Element extends EventTarget { constructor(){super();this.dataset={};this.textContent='';this.hidden=false;this.elements={};} setAttribute(k,v){this[k]=v;} removeAttribute(k){delete this[k];} }
  const toggle=new Element(), status=new Element(), controls=new Element(), tutor=new Element(), panel=new Element(), question=new Element();
  question.elements={character:{value:'nora'},csrf_token:{value:'test-token'}};
  const mapped={'[data-conversation-toggle]':toggle,'[data-conversation-status]':status,'[data-conversation-result]':new Element(),'[data-conversation-transcript]':new Element(),'[data-conversation-reply]':new Element(),'[data-conversation-link]':new Element()};
  for(const kind of ['silence','noise']) { const el=new Element();el.textContent=kind;el.dataset.signature='signed-'+kind;mapped[`[data-conversation-notice="${kind}"]`]=el; }
  controls.querySelector=s=>mapped[s];tutor.querySelector=s=>s==='[data-tutor-conversation]'?controls:s==='#tutor-question'?question:s==='details'?panel:null;
  tutor.addEventListener('tutor:read-conversation',e=>spoken.push(e.detail));
  const document=new Element();document.querySelector=()=>tutor;
  const track={getSettings:()=>({echoCancellation:true}),addEventListener(){},stop(){stopped++;}};
  class Recorder {static isTypeSupported(){return true;}constructor(){this.state='inactive';this.mimeType='audio/webm';}start(){this.state='recording';}stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable?.({data:new Blob(['test audio'])});this.onstop?.();});}}
  const node=()=>({connect(){},frequency:{},gain:{}});
  class Engine {constructor(){this.state='running';this.destination={};}resume(){return Promise.resolve();}close(){return Promise.resolve();}createMediaStreamSource(){return node();}createBiquadFilter(){return node();}createGain(){return node();}createAnalyser(){return {...node(),getFloatTimeDomainData(samples){for(let i=0;i<samples.length;i++)samples[i]=level*Math.sin(i/8);}};}}
  const window=new Element();Object.assign(window,{isSecureContext:true,MediaRecorder:Recorder,AudioContext:Engine});
  const context={window,document,navigator:{mediaDevices:{getUserMedia:async()=>({getTracks:()=>[track],getAudioTracks:()=>[track]})}},MediaRecorder:Recorder,performance:{now:()=>now},requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:key=>frames.delete(key),Event,CustomEvent,Float32Array,Blob,FormData,AbortController,queueMicrotask,fetch:async(path,options)=>{requests.push(options.body);return{ok:true,json:async()=>({transcript:'Una duda',reply:'Te ayudo',signature:'signed-reply',link:''})};}};
  vm.runInNewContext(source,context);
  return {controls,status,spoken,requests,get stopped(){return stopped;},async click(){toggle.dispatchEvent(new Event('click'));await settle();},async advance(ms,input=0){const end=now+ms;while(now<end){now=Math.min(end,now+100);level=typeof input==='function'?input(now):input;const pending=[...frames.values()];frames.clear();for(const fn of pending)fn(now);await settle();}},done(){spoken.at(-1).done();}};
}

{
 const h=harness();await h.click();await h.advance(29000);assert.equal(h.spoken.length,0);
 await h.advance(1100);assert.equal(h.spoken.length,1);assert.equal(h.spoken[0].text,'silence');assert.equal(h.controls.dataset.phase,'notifying');
 h.done();await h.advance(70000);assert.equal(h.spoken.length,1);assert.equal(h.requests.length,0);
 await h.advance(20000);assert.equal(h.stopped,1);assert.equal(h.controls.dataset.phase,'idle');
}
{
 const h=harness();await h.click();await h.advance(8500,0.06);assert.equal(h.spoken[0].text,'noise');assert.equal(h.requests.length,0);
 h.done();await h.advance(10000,0.06);assert.equal(h.spoken.length,1);assert.equal(h.requests.length,0);
 await h.advance(5000,0);await h.advance(1000,0.012);await h.advance(2000,0);
 assert.equal(h.requests.length,1);assert.equal(h.spoken.at(-1).text,'Te ayudo');
}
{
 const h=harness();await h.click();await h.advance(20000,t=>t%400<200?0.03:0.1);assert.equal(h.spoken.length,0);assert.equal(h.requests.length,0);
 await h.advance(2000,0);assert.equal(h.requests.length,1);
}
{
 const h=harness();await h.click();await h.advance(31000);const late=h.spoken[0].done;await h.click();late();await h.advance(20000);
 assert.equal(h.stopped,1);assert.equal(h.controls.dataset.phase,'idle');assert.equal(h.requests.length,0);
}
{
 const h=harness();await h.click();await h.advance(8500,0.06);h.done();await h.advance(37000,0.06);
 assert.equal(h.spoken.length,1);await h.advance(16000,0.06);assert.equal(h.spoken.length,2);assert.equal(h.requests.length,0);
}
console.log('OK: toque de silencio, cierre por inactividad, ruido sin enviar turnos, recuperación de voz, habla larga, avisos espaciados y cierre durante aviso');
