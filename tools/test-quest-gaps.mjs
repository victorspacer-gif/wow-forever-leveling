import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {setTimeout as wait} from 'node:timers/promises';
const profile=await mkdtemp(join(process.env.TMPDIR||process.cwd(),'npc-chrome-'));
const env=process.platform==='linux'?{...process.env,TMPDIR:'/proc/self/cwd'}:process.env;
const chrome=spawn(process.env.CHROMIUM||'chromium',['--headless','--disable-gpu','--disable-background-networking','--no-first-run',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{cwd:profile,env,stdio:['ignore','ignore','pipe']});
let log='';chrome.stderr.on('data',x=>log+=x);let ws;
try{
 let port;for(let i=0;i<100;i++){try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break}catch{}if(chrome.exitCode!==null)throw Error(log);await wait(100)}
 assert.ok(port,log);const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((a,b)=>{ws.addEventListener('open',a,{once:true});ws.addEventListener('error',b,{once:true})});
 const pending=new Map(),errors=[],requests=[];let serial=0;ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const cb=pending.get(d.id);pending.delete(d.id);d.error?cb?.[1](Error(d.error.message)):cb?.[0](d.result)}if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.exception?.description||d.params.exceptionDetails.text);if(d.method==='Network.requestWillBeSent')requests.push(d.params.request.url)});
 const send=(method,params={})=>new Promise((a,b)=>{const id=++serial;pending.set(id,[a,b]);ws.send(JSON.stringify({id,method,params}))});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
 const until=async expr=>{for(let i=0;i<80;i++){if(await ev(expr))return;await wait(90)}throw Error(`Timed out ${expr} ${errors}`)};
 await send('Runtime.enable');await send('Page.enable');await send('Network.enable');await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});

 const nav=async hash=>{await send('Page.navigate',{url:new URL('../quest-finder.html#'+hash,import.meta.url).href});await until(`location.hash===${JSON.stringify('#'+hash)}`)};
 await nav('quest=3883');
 await until(`!!document.querySelector('#next-panel [data-quest="92020"]')`);
 assert.match(await ev(`document.querySelector('#next-panel').innerText`),/No required follow-up.*Reported.*unconfirmed/s);
 await ev(`document.querySelector('#next-panel [data-quest="92020"]').click()`);
 await until(`location.hash==='#quest=92020' && !!document.querySelector('#pre-panel [data-quest="3883"]')`);
 assert.match(await ev(`document.querySelector('#detail').innerText`),/Pickup level 55.*Tiala Whitemane.*Summit of Eternity/s);
 assert.match(await ev(`document.querySelector('#quest-objectives').innerText`),/sketchbook.*Tiala Whitemane.*Wowhead Forever/s);
 await ev(`history.back();true`);
 await until(`location.hash==='#quest=3883' && !!document.querySelector('#next-panel [data-quest="92020"]')`);
 await nav('quest=90647');
 await until(`!!document.querySelector('#series-steps')`);
 assert.deepEqual(await ev(`[...document.querySelectorAll('#series-steps .chainstep')].map(el=>Number(el.querySelector('.id').textContent.slice(1)))`),[90647,92169,92833,93848]);
 assert.match(await ev(`document.querySelector('#detail').innerText`),/Stolen Life.*Ashes of the Legion Ascent.*A Bit of the Sky/s);
 await nav('npc=40833');
 await until(`!!document.querySelector('.npc-profile [data-quest="92020"]')`);
 assert.ok(await ev(`!!document.querySelector('.npc-profile [data-quest="93848"]')`));
 await nav('npc=9271');
 await until(`!!document.querySelector('.npc-profile [data-quest="92020"]')`);
 assert.ok(await ev(`!!document.querySelector('.npc-profile [data-quest="3883"]')`));
 await nav('quest=3883');
 await until(`!!document.querySelector('#next-panel')`);
 await ev(`(()=>{const e=document.querySelector('#language');e.value='pt-BR';e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
 assert.match(await ev(`document.querySelector('#next-panel').innerText`),/Nenhuma continuação obrigatória.*Hol'anyee.*Relatada/s);
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 assert.equal(await ev(`document.documentElement.scrollWidth<=innerWidth`),true);
 assert.deepEqual(errors,[]);
 assert.equal(requests.filter(x=>/^https?:/.test(x)).length,0);
 console.log('Quest gaps verified offline: bidirectional reported link; required Hyjal chain and prerequisite note; NPC profiles; localized labels; history; mobile width; no JS errors.');
}finally{ws?.close();chrome.kill()}
