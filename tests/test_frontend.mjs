import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const code=readFileSync(new URL('../frontend/sharing.js',import.meta.url),'utf8');
function setup({clipboard=true,share=null,canonical='https://confirmed.invalid/'}={}){
 const nodes=new Map();
 const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',open:false,listeners:{},addEventListener(n,f){this.listeners[n]=f;},showModal(){this.open=true;},close(){this.open=false;},focus(){},select(){}});return nodes.get(id);};
 let copied='',shared=null;
 const nav={};if(clipboard)nav.clipboard={writeText:async value=>{copied=value;}};
 if(share)nav.share=async value=>{shared=value;return share(value);};
 const context={URL,location:{pathname:'/',origin:'http://localhost:8000'},navigator:nav,document:{getElementById:node,querySelector:()=>canonical?{href:canonical}:null,querySelectorAll:()=>[]}};
 vm.runInNewContext(code,context);
 return {node,get copied(){return copied;},get shared(){return shared;}};
}
let s=setup();await s.node('copy-link').listeners.click();assert.equal(s.copied,'https://confirmed.invalid/');assert.match(s.node('sharing-status').textContent,/copied/);
s=setup({clipboard:false});await s.node('copy-link').listeners.click();assert.equal(s.node('share-dialog').open,true);assert.equal(s.node('share-address').value,'https://confirmed.invalid/');
s=setup({share:async()=>{}});await s.node('share-app').listeners.click();assert.equal(s.shared.url,'https://confirmed.invalid/');assert.equal(s.copied,'');
s=setup({share:async()=>{const e=Error();e.name='AbortError';throw e;}});await s.node('share-app').listeners.click();assert.equal(s.node('share-dialog').open,false);
s=setup({canonical:null});await s.node('copy-link').listeners.click();assert.equal(s.copied,'http://localhost:8000/');
s=setup();s.node('quick-guide').listeners.click();assert.equal(s.node('guide-dialog').open,true);
console.log('6 simulated sharing/guide checks passed. No real browser was used.');
