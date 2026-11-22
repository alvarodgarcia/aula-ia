// Render the same illustrated HTML used by /ayuda, check its controls, and create /ayuda/pdf.
// Requires Node.js 22+ and Chrome/Chromium. Set CHROME_PATH if it is not in a usual location.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
import {readFile, writeFile, mkdtemp, mkdir} from 'node:fs/promises';
import {createServer} from 'node:http';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {setTimeout as sleep} from 'node:timers/promises';

const root=fileURLToPath(new URL('..',import.meta.url));
const output=process.argv.find(arg=>arg.startsWith('--screenshots='))?.slice(14) || join(tmpdir(),'aula-manual-preview');
await mkdir(output,{recursive:true});
const chrome=process.env.CHROME_PATH || [
  join(process.env.ProgramFiles || '', 'Google/Chrome/Application/chrome.exe'),
  '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].find(existsSync);
assert(chrome,'Set CHROME_PATH to your Chrome/Chromium executable.');
const version=(await readFile(join(root,'VERSION'),'utf8')).trim();
const html=await readFile(join(root,'app/guide/manual.html'));
assert(html.toString().includes(`Aula IA ${version}`),'Update the guide version before building.');
const host=createServer((req,res)=>{
  if(req.url !== '/ayuda'){res.writeHead(404).end();return;}
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(html);
}).listen(0,'127.0.0.1');
await new Promise(resolve=>host.on('listening',resolve));
const profile=await mkdtemp(join(tmpdir(),'aula-manual-chrome-'));
const browser=spawn(chrome,['--headless','--disable-gpu','--disable-background-networking','--no-first-run',
  '--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'],{windowsHide:true,stdio:'ignore'});
let socket;
try {
  let port;
  for(let i=0;i<60&&!port;i++){
    try{[port]=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n');}
    catch(error){if(error.code!=='ENOENT')throw error;await sleep(100);}
  }
  assert(port,'Chrome did not start.');
  const [tab]=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
  let sequence=0,onLoad;
  const calls=new Map();
  socket.addEventListener('message',({data})=>{
    const msg=JSON.parse(data);
    if(msg.method==='Page.loadEventFired')onLoad?.();
    const pending=calls.get(msg.id);if(!pending)return;calls.delete(msg.id);
    msg.error?pending[1](new Error(msg.error.message)):pending[0](msg.result);
  });
  const call=(method,params={})=>new Promise((resolve,reject)=>{
    const id=++sequence;calls.set(id,[resolve,reject]);socket.send(JSON.stringify({id,method,params}));
  });
  const evaluate=async expression=>{
    const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
    assert(!result.exceptionDetails,JSON.stringify(result.exceptionDetails));return result.result.value;
  };
  await call('Page.enable');
  const loaded=new Promise(resolve=>{onLoad=resolve;});
  await call('Page.navigate',{url:`http://127.0.0.1:${host.address().port}/ayuda`});await loaded;
  await evaluate('document.fonts.ready');
  assert.equal(await evaluate('document.querySelectorAll("[data-mission]").length'),13);
  assert.equal(await evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),true);
  for(const width of [320,390,768,1120]){
    await call('Emulation.setDeviceMetricsOverride',{width,height:1100,deviceScaleFactor:1,mobile:width<500});
    assert.equal(await evaluate('document.documentElement.scrollWidth'),await evaluate('document.documentElement.clientWidth'));
    for(const id of ['portada','escucha','pronunciacion','adulto']){
      await evaluate(`document.getElementById('${id}').scrollIntoView({behavior:'instant'})`);
      const {data}=await call('Page.captureScreenshot',{format:'png'});
      await writeFile(join(output,`manual-${id}-${width}.png`),Buffer.from(data,'base64'));
    }
  }
  await evaluate('document.querySelector("[data-audience=primary]").click()');
  assert.equal(await evaluate('document.querySelector("#guide-progress").max'),10);
  assert.equal(await evaluate('document.querySelector("#fotos").hidden'),true);
  assert.equal(await evaluate('document.querySelector("#ingles").hidden'),false);
  await evaluate('document.querySelector("[data-audience=all]").click();document.querySelector("#escucha .done").click()');
  assert.equal(await evaluate('document.querySelector("#guide-progress").value'),1);
  assert.equal(await evaluate('JSON.parse(localStorage.getItem("aula-ia-manual-progress"))[0]'),'escucha');
  await evaluate('document.querySelector("#escucha .done").click()');
  await call('Emulation.setEmulatedMedia',{media:'print'});
  const {data}=await call('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,
    headerTemplate:'<span></span>',footerTemplate:`<div style="font-family:Arial;font-size:9px;width:100%;margin:0 14mm;color:#586078">Aula IA ${version} · Cómo usar Aula IA <span style="float:right"><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`});
  await writeFile(resolve(root,'app/guide/manual.pdf'),Buffer.from(data,'base64'));
  console.log(`OK: 13 missions, filters, local progress, images and four widths. PDF updated for ${version}. Previews: ${output}`);
} finally{socket?.close();browser.kill();host.close();}
