/* Standalone shim: replaces Claude artifact services with Netlify functions */
(()=>{
const LS={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
let name=LS.get('kt_name'),pin=LS.get('kt_pin'),role=null;
const H=()=>({'x-pin':pin||'','x-user':encodeURIComponent(name||'')});
async function api(url,opt={}){const r=await fetch(url,{...opt,headers:{...(opt.headers||{}),...H()}});if(r.status===401){LS.set('kt_pin','');location.reload();throw{code:'revoked'}}if(r.status===403)throw{code:'invalid_argument',message:'Not allowed'};if(!r.ok)throw{code:'unavailable',message:await r.text()};return r}
function gate(){return new Promise(res=>{if(name&&pin)return res();const d=document.createElement('div');d.style.cssText='position:fixed;inset:0;z-index:9999;background:linear-gradient(160deg,#18489c,#0f2a5c);display:grid;place-items:center;font:15px system-ui;color:#fff;padding:24px';
 d.innerHTML='<form style="width:100%;max-width:340px;display:grid;gap:12px"><h2 style="margin:0;font-size:26px">KUL071 Site Tracker</h2><p style="margin:0;opacity:.8">Enter your name and the team PIN.</p><input name="n" placeholder="Your name" required style="height:50px;border-radius:14px;border:0;padding:0 14px;font-size:16px"><input name="p" type="password" inputmode="numeric" placeholder="Team PIN" required style="height:50px;border-radius:14px;border:0;padding:0 14px;font-size:16px"><button style="height:52px;border-radius:14px;border:0;background:#fff;color:#0f2a5c;font-weight:800;font-size:16px">Enter</button><small id="ge" style="color:#ffb3a6"></small></form>';
 document.body.appendChild(d);d.querySelector('form').onsubmit=async e=>{e.preventDefault();name=e.target.n.value.trim();pin=e.target.p.value.trim();const r=await fetch('/api/whoami',{headers:H()});if(r.ok){LS.set('kt_name',name);LS.set('kt_pin',pin);d.remove();res()}else d.querySelector('#ge').textContent='Wrong PIN'}})}
/* db with polling */
const cache={},subs=[];const last=p=>p.split('/').pop();
const snapDoc=p=>({id:last(p),exists:p in cache,data:()=>cache[p],metadata:{fromCache:false,hasPendingWrites:false}});
const snapCol=c=>{const docs=Object.keys(cache).filter(k=>k.startsWith(c+'/')&&k.split('/').length===c.split('/').length+1).sort().map(snapDoc);return{docs,size:docs.length,empty:!docs.length,metadata:{fromCache:false,hasPendingWrites:false},docChanges:()=>[]}};
const fire=()=>subs.forEach(s=>s.kind==='doc'?s.next(snapDoc(s.p)):s.next(snapCol(s.p)));
async function pull(){try{const r=await api('/api/db');const all=await r.json();Object.keys(cache).forEach(k=>delete cache[k]);Object.assign(cache,all);fire()}catch(e){}}
let timer=null;const startPoll=()=>{if(!timer){pull();timer=setInterval(()=>{if(!document.hidden)pull()},12000)}};
document.addEventListener('visibilitychange',()=>{if(!document.hidden)pull()});
const docRef=p=>({id:last(p),path:p,get:async()=>{await pull();return snapDoc(p)},
 set:async d=>{await api('/api/db',{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify({path:p,data:d})});cache[p]=d;fire()},
 update:async d=>{const n={...(cache[p]||{}),...d};await docRef(p).set(n)},
 delete:async()=>{await api('/api/db?path='+encodeURIComponent(p),{method:'DELETE'});delete cache[p];fire()},
 onSnapshot:(next)=>{const s={kind:'doc',p,next};subs.push(s);startPoll();return()=>subs.splice(subs.indexOf(s),1)}});
const db={doc:docRef,collection:c=>({path:c,doc:id=>docRef(c+'/'+id),onSnapshot:(next)=>{const s={kind:'col',p:c,next};subs.push(s);startPoll();return()=>subs.splice(subs.indexOf(s),1)},get:async()=>{await pull();return snapCol(c)}})};
const user={id:async()=>name,isOwner:async()=>role==='admin',canEdit:async()=>role==='admin',can:async()=>true,me:async()=>({id:name,name}),profiles:async ids=>Object.fromEntries(ids.map(i=>[i,{name:i}]))};
const assets={upload:async f=>{const r=await api('/api/photo',{method:'POST',headers:{'content-type':f.type||'image/jpeg'},body:f});return r.json()},list:async()=>({assets:[]}),delete:async()=>{}};
const downloads={save:async({filename,data})=>{const b=data instanceof Blob?data:new Blob([data]);const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=filename;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},2000);return{status:'saved'}}};
const sample=async(input,opt={})=>{try{const r=await api('/api/ai',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({input})});const {text}=await r.json();opt.onText&&opt.onText({text,delta:text});return{text,truncated:false}}catch(e){throw{code:'upstream_error',message:String(e.message||e)}}};
const ready=(async()=>{await new Promise(r=>document.readyState==='loading'?document.addEventListener('DOMContentLoaded',r):r());await gate();try{const r=await api('/api/whoami');role=(await r.json()).role}catch(e){}})();
window.claude={use:async n=>{await ready;return{db,user,assets,downloads,sample}[n]||null}};
})();
