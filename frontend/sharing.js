'use strict';
(()=>{
 const byId=id=>document.getElementById(id);
 // The build inserts the real production canonical URL. Local preview uses a clean local address.
 const canonical=document.querySelector('link[rel="canonical"]');
 const address=canonical?canonical.href:new URL(location.pathname,location.origin).href;
 function showAddress(){const d=byId('share-dialog');byId('share-address').value=address;if(!d.open)d.showModal();byId('share-address').focus();byId('share-address').select();}
 async function copyAddress(){
  try{if(!navigator.clipboard?.writeText)throw Error('Clipboard unavailable');await navigator.clipboard.writeText(address);byId('sharing-status').textContent='App link copied. No recording data is included.';}
  catch{byId('sharing-status').textContent='Select and copy the app address below.';showAddress();}
 }
 byId('copy-link').addEventListener('click',copyAddress);
 byId('share-app').addEventListener('click',async()=>{
  if(navigator.share){try{await navigator.share({title:'ECG Studio',text:'Split ECG recordings into six-hour CSV files.',url:address});return;}catch(e){if(e.name==='AbortError')return;}}
  await copyAddress();showAddress();
 });
 byId('quick-guide').addEventListener('click',()=>byId('guide-dialog').showModal());
 document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>byId(b.dataset.close).close()));
})();
