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

 await showQuest(3122);
 const lateMerge=await ev(timeline);
 assert.ok(lateMerge.indexOf(3127)<lateMerge.indexOf(3129),'Mountain Giant Muisek must precede Weapons of Spirit');
 await ev(`(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async value=>{globalThis.copiedChain=value}}});document.querySelector('#copy').click()})()`);
 const copied=await ev('globalThis.copiedChain');
 assert.match(copied,/Mountain Giant Muisek.*Weapons of Spirit/s);
 await showQuest(3129);
 const earlyMerge=await ev(timeline);
 assert.ok(earlyMerge.indexOf(3122)<earlyMerge.indexOf(3123),'Return to Witch Doctor Uzer’i must precede Testing the Vessel');

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
 assert.deepEqual(await ev(timeline),[92500,92335,92317,90647,92169,92833,93848]);
 assert.deepEqual(await ev(`[...document.querySelectorAll('#pre-panel [data-quest]')].map(a=>Number(a.dataset.quest))`),[92317,92335,92500]);
 await nav('npc=40833');
 await until(`!!document.querySelector('.npc-profile [data-quest="92020"]')`);
 assert.ok(await ev(`!!document.querySelector('.npc-profile [data-quest="93848"]')`));
 await nav('npc=9271');
 await until(`!!document.querySelector('.npc-profile [data-quest="92020"]')`);
 assert.ok(await ev(`!!document.querySelector('.npc-profile [data-quest="3883"]')`));

 await showQuest(95124);
 const obj=`document.querySelector('#quest-objectives').innerText`;
 const loot=`document.querySelector('#quest-items').innerText`;
 assert.match(await ev(obj),/Wharfmaster Whizzbuzz.*79\.4, 52\.7.*upper deck.*eastern ship.*Lamora's Key.*lowest deck.*Treasure Chest.*Lamora's Loot/s);
 assert.match(await ev(loot),/Lamora's Loot #268506 · Quest objective.*Lamora's Key #268520 · Required item.*3,900 XP · 65s/s);
 assert.match(await ev(seriesText),/No required series.*Unchecked Expansion.*Observed order/s);
 assert.deepEqual(await ev(timeline),[95124]);
 assert.ok(await ev(`!!document.querySelector('#quest-objectives a[href*="629472"]')`));
 await ev(`document.querySelector('#mark').click()`);
 await send('Page.reload');
 await until(`document.querySelector('#mark')?.getAttribute('aria-pressed')==='true'`);
 await ev(`document.querySelector('#mark').click()`);
 const setSearch=async value=>ev(`(()=>{const el=document.querySelector('#search');el.value=${JSON.stringify(value)};el.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelector('#results')?.innerText;})()`);
 assert.match(await setSearch('268520'),/Admiral Lamora.*Required item: Lamora's Key/s);
 assert.match(await setSearch('Lamora’s Loot'),/Admiral Lamora.*Quest objective: Lamora's Loot/s);
 await setLanguage('pt-BR');
 assert.match(await setSearch('chave de lamora'),/Almirante Lamora.*Item necessário: Chave de Lamora/s);
 assert.match(await ev(obj),/convés superior.*Chave de Lamora.*convés mais baixo.*Saque de Lamora/s);
 await setLanguage('en');
 await nav('npc=259961');
 await until(`document.querySelectorAll('.npc-profile [data-quest="95124"]').length===2`);
 await nav('quest=93269');
 await until(`document.querySelector('#detail h2')?.innerText==='Top of the Post'`);
 assert.match(await ev(obj),/mail from Everlook.*Mount Hyjal/i);
 assert.match((await ev(places)).join(' · '),/Everlook, Winterspring.*Sebelia.*Mount Hyjal/);
 await showQuest(96018);
 assert.match(await ev(obj),/pylon/i);
 await showQuest(98517);
 assert.match(await ev(`document.querySelector('#detail').innerText`),/Zephras Isle.*Shaman/s);
 await nav('about');
 await until(`!!document.querySelector('#forever-zone-coverage')?.getClientRects().length`);
 assert.match(await ev(`document.querySelector('#forever-zone-coverage').innerText`),/Riverglades — 173 quests.*Mount Hyjal — 158 quests.*Shen'dralas — 39 quests.*Zephras Isle — 151 quests/s);

 const explorerPath=[204,203,207,205,95786,95787,95799];
 await showQuest(95799);
 assert.deepEqual(await ev(timeline),explorerPath);
 assert.deepEqual(await ev(`Array.from(document.querySelectorAll('#pre-panel [data-quest]'),el=>+el.dataset.quest)`),[95787]);
 assert.match((await ev(places)).join(' · '),/Southshore, Hillsbrad Foothills \(50\.5, 57\.0\).*Hall of Explorers, Ironforge \(77\.2, 12\.0\)/);
 assert.match(await ev(loot),/Translated Tale.*Guaranteed reward.*Ancient Voodoo Pouch.*Choose one reward.*Chainmail.*Choose one reward.*2,350 XP · 35s.*\+75 reputation with Stormwind.*\+50 reputation with Ironforge/s);
 assert.match(await setSearch('279881'),/Findings for the Explorer's League.*Choose one reward: Intrepid Explorer's Chainmail/s);
 await ev(`document.querySelector('#series-steps [data-quest="95787"]').click()`);
 await until(`(${selected})[0]===95787`);
 assert.match(await ev(obj),/left after the first boss.*skull in the pirate area.*Var'Taka.*Abyssal Dais/s);
 assert.match(await setSearch('270311'),/Take Two With Water.*Quest objective: The Fourth Tablet of I'lalai/s);
 await ev(`document.querySelector('#series-steps [data-quest="95786"]').click()`);
 await until(`(${selected})[0]===95786`);
 assert.deepEqual(await ev(timeline),[204,203,207,205,95786,95788,95787,95799,95798]);
 assert.match(await ev(seriesText),/Magics of the Drowned City.*Take Two With Water.*Findings for the Explorer's League.*After: Take Two With Water.*The Web of Magic.*After: Magics of the Drowned City/s);
 await showQuest(95798);
 assert.deepEqual(await ev(timeline),[204,203,207,205,95786,95788,95798]);
 await setLanguage('pt-BR');
 assert.match(await ev(obj),/Leve-o a Abra Cadabra em Dalaran/);
 assert.match(await ev(seriesText),/Tabuletas afogadas|Magias da Cidade Afogada.*A teia de magias/s);
 assert.match(await setSearch('História Traduzida de Ilalai'),/Achados para a Liga dos Exploradores.*Recompensa garantida: História Traduzida/s);
 for(const width of [1440,800,560,390]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:false});
  assert.deepEqual(await ev(`(()=>{const p=document.querySelector('#series').getBoundingClientRect();return Array.from(document.querySelectorAll('#series-steps *')).filter(el=>{const r=el.getBoundingClientRect();return r.width&&(r.left<p.left-1||r.right>p.right+1)}).map(el=>el.textContent);})()`),[],`Explorer timeline overflows at ${width}px`);
 }
 await send('Emulation.clearDeviceMetricsOverride');
 await setLanguage('en');
 await nav('npc=2277');
 await until(`!!document.querySelector('.npc-profile [data-quest="95799"]')`);
 await nav('npc=2916');
 await until(`!!document.querySelector('.npc-profile [data-quest="95799"]')`);

 await nav('quest=3883');
 await until(`!!document.querySelector('#next-panel')`);
 await setLanguage('pt-BR');
 assert.match(await ev(`document.querySelector('#next-panel').innerText`),/Nenhuma continuação obrigatória.*Hol'anyee.*Relatada/s);
 assert.match(await ev(seriesText),/Elos opcionais, relatados e de série.*Hol'anyee.*Relatada/s);
 const layout=`(() => {
   const panel=document.querySelector('#series'), bounds=panel.getBoundingClientRect();
   const list=panel.querySelectorAll(':scope > ol#series-steps.steps');
   const rows=Array.from(list[0]?.children || []), form=getComputedStyle(list[0] || panel);
   const markers=rows.map(row=>getComputedStyle(row,'::before'));
   const outside=r=>r.width>0&&(r.left<bounds.left-1||r.right>bounds.right+1);
   const failures=[];
   for(const e of panel.querySelectorAll('li, h3, h4, .place, .chain-rule, a, strong, p, summary, .starter, .series-top')){
     if(outside(e.getBoundingClientRect())) failures.push(e.textContent.slice(0,80));
   }
   const text=document.createTreeWalker(panel,NodeFilter.SHOW_TEXT);
   while(text.nextNode()){
     if(!text.currentNode.textContent.trim())continue;
     const range=document.createRange();range.selectNodeContents(text.currentNode);
     if(Array.from(range.getClientRects()).some(outside)) failures.push(text.currentNode.textContent.trim().slice(0,80));
   }
   return {count:list.length, rows:rows.length, validRows:rows.every(row=>row.matches('li.chainstep')&&row.getClientRects().length),
     current:rows.filter(row=>row.classList.contains('current')).length,
     highlighted:rows.length<2 || new Set(markers.map(style=>style.backgroundColor)).size>1,
     numbered:form.counterReset==='seq 0'&&markers.every(style=>style.counterIncrement==='seq 1'&&style.content.includes('counter(seq')),
     report:!!panel.querySelector(':scope > .subgroup a[data-quest="92020"]')?.getClientRects().length,
     pageOverflow:document.documentElement.scrollWidth>innerWidth, failures};
 })()`;
 const cases=new Map([[610,7],[735,4],[737,6],[3122,9],[3883,1],[90647,7],[95124,1],[95786,9],[95799,7]]);
 for(const language of ['en','pt-BR']){
  await setLanguage(language);
  for(const width of [1440,651,650,390,320]){
   await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
   for(const [id,rows] of cases){
    await showQuest(id);
    assert.deepEqual(await ev(layout),{count:1,rows,validRows:true,current:1,highlighted:true,numbered:true,
     report:id===3883,pageOverflow:false,failures:[]},`${id} at ${width}px (${language})`);
   }
  }
 }
 // Stress future imports: place names and notes can contain a single long token.
 await showQuest(95786);
 await ev(`(() => {const token='FutureImportedLongName'.repeat(10);
   document.querySelector('#series-steps .current .place').textContent=token;
   document.querySelector('#series-steps .chain-rule > span').textContent=token;
   document.querySelector('#series-steps .current strong').textContent=token;
 })()`);
 const stress=await ev(layout);
 assert.deepEqual(stress.failures,[],'Long imported text overflows the chain');
 assert.equal(stress.pageOverflow,false);
 assert.deepEqual(errors,[]);
 assert.equal(requests.filter(x=>/^https?:/.test(x)).length,0);
 console.log('Quest chains verified offline: shared timeline, branch order, visible reported links, and safe wrapping of imported text. Nine reference quests at five widths in EN/PT-BR passed, including the 650px breakpoint and 320px mobile.');
}finally{ws?.close();chrome.kill()}
