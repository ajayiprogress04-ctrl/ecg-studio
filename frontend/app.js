'use strict';
const $=id=>document.getElementById(id);
const isLocal=['localhost','127.0.0.1','[::1]'].includes(location.hostname);
function normalizeService(value){
 if(!value)return '';
 const u=new URL(value);
 const local=['localhost','127.0.0.1','[::1]'].includes(u.hostname);
 if(u.username||u.password||u.search||u.hash||u.pathname!=='/'||(!local&&u.protocol!=='https:')||(local&&(!isLocal||!['http:','https:'].includes(u.protocol))))throw Error('Enter the Python service HTTPS origin only, for example https://your-service.onrender.com. A hosted app cannot use localhost.');
 return u.origin;
}
let base='';
try{base=normalizeService(localStorage.getItem('ecg-service-origin')||window.ECG_API_URL||(isLocal?'http://localhost:5000':''));}catch{}
$('service-url').value=base;
let chosen=[],busy=false,limits=null;
const bytes=n=>new Intl.NumberFormat(undefined,{maximumFractionDigits:1}).format(n/1024**2)+' MiB';
const pause=ms=>new Promise(r=>setTimeout(r,ms));
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function appearance(value){document.body.dataset.theme=value;try{localStorage.setItem('ecg-theme',value);}catch{}}
try{$('theme').value=localStorage.getItem('ecg-theme')||'light';}catch{}
appearance($('theme').value);$('theme').onchange=()=>appearance($('theme').value);
async function api(path,options={},job){options.headers={...options.headers,...(job?{'X-Job-Token':job.token}:{})};const r=await fetch(base+path,options);let data;try{data=await r.json();}catch{throw Error('The service did not return a JSON response. Check that this is the Python backend address, not the Vercel frontend or a dashboard link.');}if(!r.ok)throw new Error(data.error||'Service request failed.');return data;}
function select(files){if(busy)return;chosen.push(...Array.from(files));renderSelection();}
function renderSelection(){$('selected').replaceChildren();for(const f of chosen){const row=element('div',undefined,'file-row');row.append(element('span',f.name),element('span',bytes(f.size)));$('selected').append(row);}$('run').disabled=busy||!chosen.length;$('notice').textContent=chosen.length?`${chosen.length} file(s) selected. Unsupported files will be identified before upload.`:'Select a recording to begin.';}
$('files').onchange=e=>{select(e.target.files);e.target.value='';};
for(const type of ['dragenter','dragover'])$('drop').addEventListener(type,e=>{e.preventDefault();$('drop').classList.add('over');});
for(const type of ['dragleave','drop'])$('drop').addEventListener(type,e=>{e.preventDefault();$('drop').classList.remove('over');});
$('drop').addEventListener('drop',e=>select(e.dataTransfer.files));
$('clear').onclick=()=>{if(!busy){chosen=[];renderSelection();}};
function download(job,name){const form=document.createElement('form');form.method='POST';form.action=base+`/jobs/${job.id}/download/${encodeURIComponent(name)}`;form.target='downloads';const token=document.createElement('input');token.type='hidden';token.name='token';token.value=job.token;form.append(token);document.body.append(form);form.submit();form.remove();}
function downloadButton(job,name,label){const b=element('button',label||'Download','secondary');b.onclick=()=>download(job,name);return b;}
async function checkService(){
 if(!base)throw Error('Python service not configured. Deploy the Python backend, then enter its HTTPS address under Service connection & privacy.');
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),20000);
 try{
  limits=await api('/health',{signal:controller.signal});
  if(limits.status!=='ok'||!Number.isFinite(limits.max_chunk_bytes)||!Number.isFinite(limits.max_file_bytes))throw Error('This address is not a compatible ECG Python service.');
  $('service').textContent=`Connected to ${base}. File limit: ${bytes(limits.max_file_bytes)}. Up to ${limits.max_jobs} retained jobs. Expiry after ${Math.round(limits.retention_seconds/3600)} hours of inactivity.`;
 }catch(error){
  if(error.name==='AbortError')throw Error('The service did not respond within 20 seconds. It may still be starting; wait and test the connection again.');
  if(error instanceof TypeError)throw Error(`Cannot connect to ${base}. Check that the backend is running over HTTPS and ECG_FRONTEND_ORIGIN is set to ${location.origin}. A browser connection error alone cannot distinguish an unavailable server from a CORS or network problem.`);
  throw error;
 }finally{clearTimeout(timer);}
}
function showConnectionError(error){$('service').textContent=error.message;$('service').className='error';}
$('save-service').onclick=async()=>{
 if(busy)return;
 const control=$('save-service');control.disabled=true;
 try{base=normalizeService($('service-url').value.trim());if(base)localStorage.setItem('ecg-service-origin',base);else localStorage.removeItem('ecg-service-origin');$('service').className='';await checkService();}
 catch(error){showConnectionError(error);}finally{control.disabled=false;}
};
checkService().catch(showConnectionError);
$('run').onclick=async()=>{
 if(busy)return;busy=true;$('run').disabled=true;$('save-service').disabled=true;$('service-url').disabled=true;$('files').disabled=true;$('clear').disabled=true;$('results-section').hidden=false;
 const batch=chosen;chosen=[];let success=0,failed=0;
 try{await checkService();}catch(error){busy=false;chosen=batch;renderSelection();$('files').disabled=false;$('clear').disabled=false;$('save-service').disabled=false;$('service-url').disabled=false;showConnectionError(error);$('connection-settings').open=true;$('notice').textContent=error.message;return;}
 for(let idx=0;idx<batch.length;idx++){
  const file=batch[idx],card=element('article',undefined,'job'),title=element('h3',file.name),status=element('p','Validating…'),meter=element('progress'),actions=element('div',undefined,'actions');meter.max=100;meter.value=0;card.append(title,status,meter,actions);$('results').append(card);let job;
  $('notice').textContent=`Recording ${idx+1} of ${batch.length}. ${success} completed; ${failed} failed.`;
  try{
   if(!file.name.toLowerCase().endsWith('.csv')||!file.size)throw Error('Select a nonempty CSV file.');
   if(file.size>limits.max_file_bytes)throw Error('File exceeds the configured service capacity.');
   const sample=await file.slice(0,65536).text();
   if(!sample.includes(',')||sample.includes('\u0000'))throw Error('This does not appear to be a comma-separated text export.');
   job=await api('/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:file.name,size:file.size})});
   let offset=0;
   while(offset<file.size){
    const end=Math.min(offset+limits.max_chunk_bytes,file.size);let sent=false;
    for(let attempt=0;attempt<3&&!sent;attempt++){
     try{const response=await api(`/jobs/${job.id}/upload`,{method:'PUT',headers:{'Content-Type':'application/octet-stream','X-Upload-Offset':String(offset)},body:file.slice(offset,end)},job);offset=response.offset;sent=true;}
     catch(error){if(attempt===2)throw error;await pause(1000);const current=await api(`/jobs/${job.id}`,{},job);if(current.offset===end){offset=end;sent=true;}else if(current.offset!==offset)throw Error('Upload offset changed unexpectedly. Delete this job and retry.');}
    }
    meter.value=offset/file.size*100;status.textContent=`Uploading: ${bytes(offset)} / ${bytes(file.size)} (${Math.floor(meter.value)}%)`;
   }
   await api(`/jobs/${job.id}/start`,{method:'POST'},job);meter.removeAttribute('value');
   let state,connectionFailures=0;
   while(true){
    try{state=await api(`/jobs/${job.id}`,{},job);connectionFailures=0;}catch(error){connectionFailures++;if(connectionFailures>=10)throw Error('Unable to retrieve job status after repeated attempts. The server may still be processing; this job has not been marked successful.');status.textContent='Connection interrupted. Retrying job status in 3 seconds…';await pause(3000);continue;}
    if(state.state==='complete'||state.state==='failed')break;
    status.textContent=state.state==='processing'?`Processing: ${(state.valid_rows||0).toLocaleString()} valid rows · ${state.chunks||0} chunks · ${(state.discarded_rows||0).toLocaleString()} discarded rows`:state.state==='packaging'?'Preparing ZIP archive…':'Queued for the Python processor…';await pause(1000);
   }
   if(state.state==='failed')throw Error(state.error);
   success++;meter.value=100;status.className='success';status.textContent=`Complete · ${state.outputs.length} files · ${state.valid_rows.toLocaleString()} valid rows · ${state.discarded_rows.toLocaleString()} discarded rows (may include column header).`;
   actions.append(downloadButton(job,'results.zip','Download ZIP'));
   const list=element('details'),summary=element('summary','Individual output files');list.append(summary);
   for(const out of state.outputs){const row=element('div',undefined,'output');row.append(element('span',`${out.name} · ${out.rows.toLocaleString()} rows · ${bytes(out.bytes)}`),downloadButton(job,out.name));list.append(row);}card.append(list);
  }catch(error){failed++;meter.hidden=true;status.className='error';status.textContent=error.message||'Processing failed. Check the service and retry.';}
  if(job){const del=element('button','Delete job','secondary');del.onclick=async()=>{del.disabled=true;try{await api(`/jobs/${job.id}`,{method:'DELETE'},job);card.replaceChildren(title,element('p','Job files deleted.'));}catch(error){del.disabled=false;status.textContent=error.message;}};actions.append(del);}
 }
 busy=false;$('save-service').disabled=false;$('service-url').disabled=false;$('files').disabled=false;$('clear').disabled=false;renderSelection();$('notice').textContent=`Batch finished: ${success} completed; ${failed} failed. You can choose another batch.`;
};
