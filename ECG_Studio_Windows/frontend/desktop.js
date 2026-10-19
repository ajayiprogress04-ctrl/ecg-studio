'use strict';
const $=id=>document.getElementById(id),token=document.querySelector('meta[name="desktop-token"]').content;
let state=null,picker=false,polling=false,closed=false,lastRender='';
const formatBytes=n=>new Intl.NumberFormat(undefined,{maximumFractionDigits:1}).format(n/1024**3)+' GiB';
const number=n=>new Intl.NumberFormat().format(n||0);
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function appearance(value){document.body.dataset.theme=value;try{localStorage.setItem('ecg-theme',value);}catch{}}
try{$('theme').value=localStorage.getItem('ecg-theme')||'light';}catch{}
appearance($('theme').value);$('theme').onchange=async()=>{appearance($('theme').value);try{state=await api('theme',{theme:$('theme').value});render();}catch(error){showError(error);}};
$('quick-guide').onclick=()=>$('guide-dialog').showModal();$('close-guide').onclick=()=>$('guide-dialog').close();
async function api(route,body){const r=await fetch('/api/'+route,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json','X-Desktop-Token':token},...(body===undefined?{}:{body:JSON.stringify(body)})});let data;try{data=await r.json();}catch{throw Error('The local application is not responding. Check that its launcher window is still open.');}if(!r.ok)throw Error(data.error||'Operation failed.');return data;}
function controls(){const busy=state?.busy||false;for(const id of ['choose-files','choose-folder','clear'])$(id).disabled=busy||picker;$('start').disabled=busy||picker||!state?.files.length||!state?.output_root;$('quit').disabled=busy||picker;$('cancel').hidden=!busy;$('cancel').disabled=!!state?.cancel_requested;}
function render(){
 if(state.theme){$('theme').value=state.theme;appearance(state.theme);}
 controls();const signature=JSON.stringify(state);if(signature===lastRender)return;lastRender=signature;
 $('selected').replaceChildren();if(!state.files.length)$('selected').append(el('p','No recordings selected.','fine'));
 for(const f of state.files){const row=el('div',undefined,'file-row');row.append(el('span',f.name),el('span',formatBytes(f.bytes)));$('selected').append(row);}
 $('output-root').textContent=state.output_root||'No output folder selected.';
 $('results-section').hidden=!state.jobs.length;$('batch-path').textContent=state.batch_folder;
 const complete=state.jobs.filter(j=>j.status==='complete').length,failed=state.jobs.filter(j=>j.status==='failed').length,cancelled=state.jobs.filter(j=>j.status==='cancelled').length;
 $('status').textContent=state.busy?(state.cancel_requested?'Stopping after the current chunk…':`Processing batch · ${complete} completed · ${failed} failed`):state.finished?`Batch finished · ${complete} completed · ${failed} failed · ${cancelled} stopped`:'Choose recordings and an output folder to begin.';
 $('results').replaceChildren();
 state.jobs.forEach((j,i)=>{const card=el('article',undefined,'job');card.append(el('h3',j.name));const status=el('p',j.status==='complete'?`${number(j.valid_rows)} valid rows · ${j.outputs.length} files · ${number(j.discarded_rows)} discarded rows`:`${j.message}${j.chunks?' · '+number(j.valid_rows)+' valid rows · '+j.chunks+' chunks':''}`,j.status==='failed'?'error':j.status==='complete'?'success':'');card.append(el('div',j.status,'state-label'),status);
 if(j.status==='processing'){const p=el('progress');p.removeAttribute('value');card.append(p);}
 if(j.status==='complete'){const b=el('button','Open output folder','secondary');b.onclick=()=>api('open-folder',{index:i}).catch(showError);card.append(b);const d=el('details');d.append(el('summary','Saved files'));for(const out of j.outputs)d.append(el('div',`${out.name} · ${number(out.rows)} rows · ${formatBytes(out.bytes)}`,'output'));card.append(d);} $('results').append(card);});
}
function showError(error){$('status').textContent=error.message||'The local application could not be reached.';$('status').className='error';}
async function pick(kind){picker=true;controls();$('status').className='';$('status').textContent='Choose in the Windows dialog. If it is behind this browser, use Alt+Tab to find it.';try{state=await api(kind,{});render();}catch(error){showError(error);}finally{picker=false;controls();}}
$('choose-files').onclick=()=>pick('choose-files');$('choose-folder').onclick=()=>pick('choose-folder');
$('clear').onclick=async()=>{try{state=await api('clear',{});render();}catch(error){showError(error);}};
$('start').onclick=async()=>{if(state?.busy)return;$('start').disabled=true;$('status').className='';try{state=await api('start',{});render();}catch(error){showError(error);controls();}};
$('cancel').onclick=async()=>{try{state=await api('cancel',{});render();}catch(error){showError(error);}};
$('open-batch').onclick=()=>api('open-folder',{}).catch(showError);
$('quit').onclick=async()=>{try{await api('quit',{});closed=true;document.querySelector('main').replaceChildren(el('div','ECG Studio has closed. Your saved output files remain in the chosen folder. You can close this tab.','closed'));}catch(error){showError(error);}};
async function poll(){if(closed||polling||picker)return;polling=true;try{state=await api('state');render();}catch(error){showError(error);}finally{polling=false;}}
poll();setInterval(poll,1000);
