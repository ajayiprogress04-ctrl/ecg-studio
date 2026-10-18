import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync(new URL('../frontend/app.js',import.meta.url),'utf8');
function context(hostname,configured=null){
 const elements=new Map(),saved=new Map();
 const node=id=>{if(!elements.has(id))elements.set(id,{value:'',textContent:'',className:'',classList:{add(){},remove(){}},addEventListener(){},replaceChildren(){},append(){}});return elements.get(id);};
 const ctx={window:{ECG_API_URL:configured},location:{hostname,origin:'https://app.example'},document:{body:{dataset:{}},getElementById:node,createElement:()=>node(Math.random())},localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)},Intl,URL,AbortController,setTimeout,clearTimeout,fetch:async()=>({ok:true,json:async()=>({status:'ok',max_chunk_bytes:8388608,max_file_bytes:1000000,max_jobs:8,retention_seconds:86400})})};
 vm.runInNewContext(source+'\nglobalThis.apiTest={normalizeService,checkService,getBase:()=>base};',ctx);return {ctx,node};
}
let c=context('app.example');assert.equal(c.ctx.apiTest.getBase(),'');await assert.rejects(c.ctx.apiTest.checkService(),/not configured/);
assert.throws(()=>c.ctx.apiTest.normalizeService('http://localhost:5000'),/hosted app cannot use localhost/);
assert.throws(()=>c.ctx.apiTest.normalizeService('http://api.example'),/HTTPS/);
assert.equal(c.ctx.apiTest.normalizeService('https://api.example/'),'https://api.example');
c=context('app.example','https://api.example');await c.ctx.apiTest.checkService();assert.match(c.node('service').textContent,/Connected to https:\/\/api.example/);
c=context('localhost');assert.equal(c.ctx.apiTest.getBase(),'http://localhost:5000');await c.ctx.apiTest.checkService();
console.log('6 simulated connection checks passed. No live backend was used.');
