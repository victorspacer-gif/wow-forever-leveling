import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const html=await readFile(process.argv[2] || new URL('../quest-finder.html',import.meta.url),'utf8');
const data=JSON.parse(html.match(/<script id="quest-data" type="application\/json">(.*?)<\/script>/s)[1]);
const kinds=new Set(['ALL','ANY','Active','Count','Breadcrumb','Suggested link','Series','Reported','Check source']);
for(const [id,quest] of Object.entries(data.quests)){
 assert.match(id,/^[1-9]\d*$/,'Malformed quest ID');
 const seen=new Set();
 for(const edge of quest.pre || []){
  const [from,kind,source,note]=edge, key=`${from}:${kind}`;
  assert.ok(Array.isArray(edge)&&edge.length===4&&typeof note==='string'&&kinds.has(kind),`Invalid relationship on quest #${id}`);
  assert.ok(Number.isSafeInteger(from)&&from!==Number(id)&&Object.hasOwn(data.quests,from),`Invalid prerequisite #${from} on quest #${id}`);
  assert.ok(Number.isSafeInteger(source)&&Object.hasOwn(data.sources,source)&&String(data.sources[source][1]).startsWith('https://'),`Missing or invalid source #${source} on quest #${id}`);
  assert.ok(!seen.has(key),`Duplicate relationship ${key} on quest #${id}`);
  seen.add(key);
 }
}
// Exercise the page's own graph logic against every record, without rendering
// thousands of pages; test-quest-gaps.mjs covers rendered browser behavior.
const plain=html.slice(html.indexOf('const hard'),html.indexOf('const questName'));
const walk=html.slice(html.indexOf('function walk('),html.indexOf('function edgeCard('));
const rows=html.slice(html.indexOf('function seriesRows('),html.indexOf('function optionalLinks('));
assert.ok(plain.includes('const ord') && walk.includes('strictPath') && rows.startsWith('function seriesRows('));
const Q=data.quests, ids=Object.keys(Q).map(Number);
const result=vm.runInNewContext(plain+'\n'+walk+'\n'+rows+`
 let branching=0, linked=0;
 for(const id of ids){
   const before=walk(id,pre), later=walk(id,after), seq=strictPath(id);
   const expected=new Set([...before.distance.keys(),id,...later.distance.keys()]);
   const steps=seq || [...seriesRows(id,before,true).map(r=>r.quest),id,...seriesRows(id,later,false).map(r=>r.quest)];
   const position=new Map(steps.map((qid,i)=>[qid,i]));
   assert.equal(steps.length,position.size,'Duplicate step: '+id);
   assert.equal(position.size,expected.size,'Lost step: '+id);
   for(const qid of expected) assert.ok(position.has(qid),'Lost step: '+id+' -> '+qid);
   for(const qid of steps){
     for(const [p,kind,sourceId] of pre(qid)){
       assert.ok(Q[p] && source[sourceId],'Broken relationship or source on '+qid);
       if(hard(kind) && position.has(p)) assert.ok(position.get(p)<position.get(qid),'Backwards edge on '+id+': '+p+' -> '+qid);
     }
   }
   if(!seq) branching++;
   if(expected.size>1) linked++;
 }
 ({checked:ids.length,linked,branching});`,{Q,ids,source:data.sources,assert});
assert.equal(result.checked,ids.length);
assert.ok(result.branching>0 && result.linked>result.branching);
console.log(`Checked all ${result.checked} quest timelines (${result.linked} linked, ${result.branching} branching): unique steps, valid references, no prerequisites below their follow-ups.`);
