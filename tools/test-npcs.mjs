import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {setTimeout as wait} from 'node:timers/promises';
const profile=await mkdtemp(join(process.env.TMPDIR||process.cwd(),'npc-chrome-'));
const chrome=spawn(process.env.CHROMIUM||'chromium',['--headless','--disable-gpu','--disable-background-networking','--no-first-run',`--user-data-dir=${profile}`,'--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','about:blank'],{cwd:profile,stdio:['ignore','ignore','pipe']});
let log='';chrome.stderr.on('data',x=>log+=x);let ws;
try{
 let port;for(let i=0;i<250;i++){try{port=(await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break}catch{}if(chrome.exitCode!==null)throw Error(log);await wait(100)}
 assert.ok(port,log);const targets=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();ws=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise((a,b)=>{ws.addEventListener('open',a,{once:true});ws.addEventListener('error',b,{once:true})});
 const pending=new Map(),errors=[],requests=[];let serial=0;ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const cb=pending.get(d.id);pending.delete(d.id);d.error?cb?.[1](Error(d.error.message)):cb?.[0](d.result)}if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.exception?.description||d.params.exceptionDetails.text);if(d.method==='Network.requestWillBeSent')requests.push(d.params.request.url)});
 const send=(method,params={})=>new Promise((a,b)=>{const id=++serial;pending.set(id,[a,b]);ws.send(JSON.stringify({id,method,params}))});
 const ev=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value};
 const until=async expr=>{for(let i=0;i<80;i++){if(await ev(expr))return;await wait(90)}throw Error(`Timed out ${expr} ${errors}`)};
 await send('Runtime.enable');await send('Page.enable');await send('Network.enable');await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
 await send('Page.navigate',{url:new URL('../quest-finder.html#npc=197',import.meta.url).href});
 await until(`document.querySelector('.npc-profile h3')?.textContent.includes('McBride')`);
 if(process.env.NPC_SCREENSHOT){const shot=await send('Page.captureScreenshot',{format:'png'});await writeFile(process.env.NPC_SCREENSHOT,Buffer.from(shot.data,'base64'))}
 assert.equal(await ev(`document.querySelector('[data-view=npc]').getAttribute('aria-pressed')`),'true');
 assert.ok(await ev(`!!document.querySelector('.npc-profile [data-quest="7"]')`));
 assert.match(await ev(`document.querySelector('.npc-profile').textContent`),/Quests started.*Quests ended/s);
 await ev(`document.querySelector('.npc-profile [data-quest="7"]').click()`);await until(`location.hash==='#quest=7' && !document.querySelector('#quest-view').hidden`);
 await ev(`history.back();true`);await until(`location.hash==='#npc=197' && !document.querySelector('#npc-view').hidden`);
 await ev(`(()=>{const e=document.querySelector('#npc-search');e.value='delegado durao';e.dispatchEvent(new Event('input',{bubbles:true}))})()`);
 assert.ok(await ev(`!!document.querySelector('[data-npc="240"]')`));await ev(`document.querySelector('[data-npc="240"]').click()`);
 assert.equal(await ev('location.hash'),'#npc=240');
 await ev(`(()=>{const e=document.querySelector('#language');e.value='pt-BR';e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
 assert.match(await ev(`document.querySelector('.npc-profile h3').textContent`),/Delegado Durão/);
 assert.match(await ev(`document.querySelector('.npc-profile').textContent`),/Missões iniciadas.*Missões concluídas/s);
 await send('Page.reload');await until(`location.hash==='#npc=240' && document.querySelector('.npc-profile h3')?.textContent.includes('Delegado')`);
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 assert.equal(await ev(`document.documentElement.scrollWidth<=innerWidth`),true);
 const unnamed=await ev(`Object.values(NPC_QUEST_DATA.npcs).find(n=>!n.name&&!n.namePtBR)?.id`);assert.ok(unnamed);
 await ev(`location.hash='#npc='+${unnamed}`);await until(`document.querySelector('.npc-profile h3')?.textContent.includes('#${unnamed}')`);
 assert.equal(requests.filter(x=>/^https?:/.test(x)).length,0);assert.deepEqual(errors,[]);
 console.log('NPC profiles validated offline: deep links, ID/name search including PT-BR and accents, start/end quests, quest navigation and Back, localization and reload, unnamed IDs, mobile width, no runtime errors or remote requests.');
}finally{ws?.close();chrome.kill()}
