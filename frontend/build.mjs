import { readFile,writeFile,rm,mkdir,cp } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root=path.dirname(fileURLToPath(import.meta.url));
const raw=process.env.ECG_PUBLIC_URL||(process.env.VERCEL_PROJECT_PRODUCTION_URL?'https://'+process.env.VERCEL_PROJECT_PRODUCTION_URL:'');
if(!raw)throw Error('Set ECG_PUBLIC_URL to the actual HTTPS production origin, or enable Vercel system environment variables.');
const url=new URL(raw);
if(url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/'||url.hostname==='localhost')throw Error('ECG_PUBLIC_URL must be an HTTPS origin without a path, credentials, query or fragment.');
const origin=url.origin;
const esc=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const metadata=`<link rel="canonical" href="${esc(origin)}/">
<meta property="og:type" content="website"><meta property="og:site_name" content="ECG Studio">
<meta property="og:title" content="ECG Studio · File Splitter"><meta property="og:description" content="Long recordings. Manageable files. Split ECG CSV recordings into six-hour windows.">
<meta property="og:url" content="${esc(origin)}/"><meta property="og:image" content="${esc(origin)}/assets/social-preview.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="ECG Studio ECG emblem and six-hour CSV splitting">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="ECG Studio · File Splitter"><meta name="twitter:description" content="Long recordings. Manageable files."><meta name="twitter:image" content="${esc(origin)}/assets/social-preview.png">`;
await rm(path.join(root,'dist'),{recursive:true,force:true});await mkdir(path.join(root,'dist'));
for(const f of ['index.html','styles.css','app.js','sharing.js','config.js','assets'])await cp(path.join(root,f),path.join(root,'dist',f),{recursive:true});
const html=(await readFile(path.join(root,'index.html'),'utf8')).replace('<!-- PRODUCTION_METADATA -->',metadata);
await writeFile(path.join(root,'dist/index.html'),html);
if(process.env.ECG_API_URL){const api=new URL(process.env.ECG_API_URL);if(api.protocol!=='https:'||api.username||api.password||api.search||api.hash||api.pathname!=='/')throw Error('ECG_API_URL must be the Python service HTTPS origin.');await writeFile(path.join(root,'dist/config.js'),'window.ECG_API_URL = '+JSON.stringify(api.origin)+';\n');}
console.log('Built static frontend with production canonical and sharing metadata.');
