'use strict';
(()=>{
 const $=id=>document.getElementById(id);
 let download='';
 const safeLink=(value,allowEmail=false)=>{try{if(allowEmail&&typeof value==='string'&&/^mailto:[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9.-]+$/.test(value))return value;const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:'';}catch{return '';}};
 function show(dialog){if(!$(dialog).open)$(dialog).showModal();}
 $('about-developer').addEventListener('click',()=>show('about-dialog'));
 $('share-desktop').addEventListener('click',()=>show('share-dialog'));
 document.querySelectorAll('[data-dismiss]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.dismiss).close()));
 function showText(id,value){if(typeof value==='string'&&value.trim()){$(id).textContent=value.trim();$(id).hidden=false;}}
 fetch('/developer.json').then(r=>{if(!r.ok)throw Error('Profile unavailable');return r.json();}).then(p=>{
  showText('developer-name',p.name);showText('developer-role',p.role);showText('developer-biography',p.biography);
  for(const q of Array.isArray(p.qualifications)?p.qualifications:[]){if(typeof q!=='string'||!q.trim())continue;const li=document.createElement('li');li.textContent=q;$('developer-qualifications').append(li);$('developer-qualifications').hidden=false;}
  // Portraits must be bundled local assets; the app never fetches a remote profile image.
  if(typeof p.portrait==='string'&&/^assets\/[a-zA-Z0-9_/-]+\.(png|jpg|jpeg|webp)$/i.test(p.portrait)&&!p.portrait.includes('..')){$('developer-portrait').src=p.portrait;$('developer-portrait').hidden=false;}
  for(const link of Array.isArray(p.links)?p.links:[]){const url=safeLink(link.url,true);if(!url||typeof link.label!=='string')continue;const a=document.createElement('a');a.href=url;a.textContent=link.label;a.target='_blank';a.rel='noopener noreferrer';$('developer-links').append(a);$('developer-links').hidden=false;}
  download=safeLink(p.download_url);if(download){$('download-address').value=download;$('public-download').hidden=false;}
 }).catch(()=>{});
 async function copy(){
  if(!download)return;
  try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(download);$('share-feedback').textContent='Installer download link copied.';}
  catch{$('download-address').focus();$('download-address').select();$('share-feedback').textContent='Select and copy the download address above.';}
 }
 $('copy-download').addEventListener('click',copy);
 $('native-share-download').addEventListener('click',async()=>{if(!download)return;if(navigator.share){try{await navigator.share({title:'ECG Studio for Windows',text:'Install ECG Studio to split ECG recordings locally.',url:download});return;}catch(e){if(e.name==='AbortError')return;}}await copy();});
})();
