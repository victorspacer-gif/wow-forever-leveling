import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp,readFile} from 'node:fs/promises';
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
 const timeline=`[...document.querySelectorAll('ol#series-steps > li.chainstep')].map(el=>Number(el.querySelector('.id').textContent.slice(1)))`;
 const selected=`[...document.querySelectorAll('#series-steps .current [aria-current="step"]')].map(el=>Number(el.nextElementSibling.textContent.slice(1)))`;
 const showQuest=async id=>{await nav('quest='+id);await until(`(${selected})[0]===${id}`);assert.deepEqual(await ev(selected),[id]);};
 const setLanguage=async lang=>{await ev(`(()=>{const e=document.querySelector('#language');e.value=${JSON.stringify(lang)};e.dispatchEvent(new Event('change',{bubbles:true}))})()`);};

 await showQuest(610);
 await setLanguage('en');
 assert.deepEqual(await ev(timeline),[616,578,601,602,603,610,611]);
 assert.equal(await ev(`document.querySelectorAll('#series-steps .chain-rule').length`),0);
 await showQuest(735);
 assert.deepEqual(await ev(timeline),[709,727,735,737]);
 const seriesText=`document.querySelector('#series').innerText`;
 assert.match(await ev(seriesText),/2 quests before · 1 quest after.*not a required route.*Required.*Selected.*One of/s);
 assert.match(await ev(`document.querySelector('#series-steps [data-quest="737"]').closest('li').innerText`),/One of.*After: The Star, the Hand and the Heart/s);
 assert.ok(await ev(`document.querySelector('#series-steps [data-quest="737"]').closest('li').querySelector('.chain-rule .source a')?.href`));
 await ev(`document.querySelector('#series-steps [data-quest="737"]').click()`);
 await until(`location.hash==='#quest=737' && (${selected})[0]===737`);
 assert.deepEqual((await ev(timeline)).sort((a,b)=>a-b),[709,727,728,735,736,737]);
 assert.equal(await ev(`document.querySelectorAll('#series-steps .chain-rule .pill.info').length`),2);
 assert.equal(await ev(`document.querySelector('#series-steps [data-quest="709"]').closest('li').querySelectorAll('.chain-rule').length`),2);
 await ev(`history.back();true`);
 await until(`location.hash==='#quest=735' && (${selected})[0]===735`);
 await setLanguage('pt-BR');
 assert.match(await ev(seriesText),/2 missões antes · 1 missão depois.*não uma rota obrigatória.*Obrigatória.*Selecionada.*Uma de.*Depois de:/s);
 for(const width of [1440,800,560,390]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:false});
  assert.deepEqual(await ev(`(()=>{const panel=document.querySelector('#series').getBoundingClientRect();return [...document.querySelectorAll('#series-steps *')].filter(el=>{const r=el.getBoundingClientRect();return r.left<panel.left-1||r.right>panel.right+1}).map(el=>el.textContent)})()`),[],`series overflow at ${width}px`);
 }
 await send('Emulation.clearDeviceMetricsOverride');
 await setLanguage('en');

 const places=`[...document.querySelectorAll('.quest-head .locations dd')].map(el=>el.textContent)`;
 await showQuest(583);
 const hemet='Hemet Nesingwary — Stranglethorn Vale (35.7, 10.8)';
 assert.deepEqual(await ev(places),['Barnil Stonepot — Stranglethorn Vale (35.7, 10.5)',hemet]);
 assert.equal(await ev(`document.querySelector('#series-steps [data-quest="194"]').closest('li').querySelector('.place').textContent`),hemet);
 await showQuest(194);
 assert.deepEqual(await ev(places),[hemet,hemet]);
 await showQuest(5781);
 const tirion='Tirion Fordring — Eastern Plaguelands (5.2, 35.6)';
 assert.deepEqual(await ev(places),[tirion,tirion]);
 await showQuest(7067);
 const patrol='Centaur Pariah — southern Desolace (patrols)';
 assert.deepEqual(await ev(places),[patrol,patrol]);

 await nav('quest=3883');
 await until(`!!document.querySelector('#next-panel [data-quest="92020"]')`);
 assert.deepEqual(await ev(timeline),[3883]);
 assert.match(await ev(`document.querySelector('#next-panel').innerText`),/No required follow-up.*Reported.*unconfirmed/s);
 assert.match(await ev(`document.querySelector('#series').innerText`),/No required series.*not counted as required progression.*Big Book of Big Lizards.*Reported/s);
 assert.ok(await ev(`!!document.querySelector('#series section [data-quest="92020"]')`));
 await ev(`document.querySelector('#series [data-quest="92020"]').click()`);
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
 await setLanguage('pt-BR');
 assert.match(await ev(`document.querySelector('#next-panel').innerText`),/Nenhuma continuação obrigatória.*Hol'anyee.*Relatada/s);
 assert.match(await ev(`document.querySelector('#series').innerText`),/Elos opcionais, relatados e de série.*Hol'anyee.*Relatada/s);
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 assert.equal(await ev(`document.documentElement.scrollWidth<=innerWidth`),true);
 assert.deepEqual(errors,[]);
 assert.equal(requests.filter(x=>/^https?:/.test(x)).length,0);
 console.log('Quest chains and location fixes verified offline: shared timeline; branch rules and sources; corrected pickups and turn-ins; Hyjal chain; NPC profiles; history; EN/PT-BR; desktop and mobile widths; no JS errors.');
}finally{ws?.close();chrome.kill()}
