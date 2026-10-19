import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const script=readFileSync(new URL('../frontend/about.js',import.meta.url),'utf8');
async function setup(profile){
 const elements=new Map();let copied='';
 const node=id=>{if(!elements.has(id))elements.set(id,{hidden:true,value:'',textContent:'',children:[],handlers:{},open:false,addEventListener(n,f){this.handlers[n]=f;},append(child){this.children.push(child);},showModal(){this.open=true;},close(){this.open=false;},focus(){},select(){}});return elements.get(id);};
 let seq=0;
 const context={URL,navigator:{clipboard:{writeText:async value=>{copied=value;}}},fetch:async()=>({ok:true,json:async()=>profile}),document:{getElementById:node,querySelectorAll:()=>[],createElement:()=>node('generated-'+seq++)}};
 vm.runInNewContext(script,context);await new Promise(r=>setImmediate(r));
 return {node,get copied(){return copied;}};
}
const approved=JSON.parse(readFileSync(new URL('../frontend/developer.json',import.meta.url),'utf8'));
let test=await setup(approved);assert.equal(test.node('developer-name').textContent,'Progress Ajayi');assert.match(test.node('developer-biography').textContent,/Human Physiology/);assert.equal(test.node('developer-qualifications').children.length,3);assert.equal(test.node('developer-links').children.length,3);assert.equal(test.node('public-download').hidden,true);test.node('about-developer').handlers.click();assert.equal(test.node('about-dialog').open,true);test.node('share-desktop').handlers.click();assert.equal(test.node('share-dialog').open,true);
test=await setup({name:'<script>unsafe</script>',portrait:'https://outside.example/portrait.jpg',links:[{label:'bad',url:'javascript:alert(1)'}],download_url:'http://127.0.0.1:4000/'});assert.equal(test.node('developer-name').textContent,'<script>unsafe</script>');assert.equal(test.node('developer-portrait').hidden,true);assert.equal(test.node('developer-links').children.length,0);assert.equal(test.node('public-download').hidden,true);
test=await setup({download_url:'https://downloads.example/ecg-studio/'});assert.equal(test.node('public-download').hidden,false);await test.node('copy-download').handlers.click();assert.equal(test.copied,'https://downloads.example/ecg-studio/');
console.log('Approved profile rendering, dialog opening, safe links/local portrait rules and public download copying passed in a simulated DOM.');
