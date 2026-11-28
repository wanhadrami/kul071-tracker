import {getStore} from '@netlify/blobs';import seed from './srp-seed.mjs';
// Every Tuesday 23:59 MYT (15:59 UTC): if this week's SRP was not generated, save it to history from the latest data.
const wk=s=>74+Math.round((Date.parse(s)-Date.parse('2026-11-18'))/6048e5),wid=w=>'W'+String(w).padStart(3,'0');
export async function snap(st,now=Date.now()){const cut=new Date(now+8*36e5+864e5).toISOString().slice(0,10),W=wk(cut);
 if(await st.get('srpg/'+wid(W),{type:'json'}))return{skip:'already generated',W};
 const {blobs}=await st.list(),D={};await Promise.all(blobs.filter(b=>/^srp[gwo]\//.test(b.key)).map(async b=>{D[b.key]=await st.get(b.key,{type:'json'})}));
 const SWK={...seed.SEED};for(const[k,v] of Object.entries(D))if(k.startsWith('srpg/')&&Number.isInteger(v?.w))SWK[v.w]=v;for(const[k,v] of Object.entries(D))if(k.startsWith('srpw/')&&Number.isInteger(v?.w))SWK[v.w]=v;
 const prev=Object.values(SWK).filter(x=>x.w<W).sort((a,b)=>b.w-a.w)[0],cur=SWK[W],v={};
 for(const id of Object.keys(seed.base)){const o=D['srpo/'+wid(W)+'_'+id]||(D['srpo/'+id]?.w===W?D['srpo/'+id]:null);v[id]=(o&&Array.isArray(o.v)&&o.v)||cur?.v?.[id]||prev?.v?.[id]||seed.base[id]}
 const doc={w:W,cut,v,at:now,by:'Auto · Tue 23:59',auto:true,rev:[]};await st.setJSON('srpg/'+wid(W),doc);return{saved:W,cut}}
export default async()=>{const r=await snap(getStore({name:'kul071',consistency:'strong'}));console.log(JSON.stringify(r));return new Response('ok')};
export const config={schedule:'59 15 * * 2'};
