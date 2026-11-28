import {getStore} from '@netlify/blobs';import {role,deny} from './_auth.mjs';import {createHash} from 'node:crypto';
const EH='b03ddf3ca2e714a6548e7495e2a03f5e824eaac9837cd7f159c67b90fb4b7342';
const ADMIN_ONLY=['base/','p6sum/'];
export default async req=>{const r=role(req);if(!r)return deny();const st=getStore({name:'kul071',consistency:'strong'});const u=new URL(req.url);
 if(req.method==='GET'){const {blobs}=await st.list();const out={};await Promise.all(blobs.map(async b=>{out[b.key]=await st.get(b.key,{type:'json'})}));return Response.json(out)}
 const path=req.method==='DELETE'?u.searchParams.get('path'):(await req.clone().json()).path;
 if(!path||!/^[A-Za-z0-9_\-.~:@+\/]+$/.test(path))return new Response('bad path',{status:400});
 if(path.startsWith('srpw/')&&createHash('sha256').update(req.headers.get('x-edit')||'').digest('hex')!==EH)return new Response('password',{status:403});
 if(ADMIN_ONLY.some(p=>path.startsWith(p))&&r!=='admin')return new Response('admin only',{status:403});
 if(req.method==='PUT'){const {data}=await req.json();
  const day=o=>new Date(Date.now()+8*36e5+o*864e5).toISOString().slice(0,10),T=day(1);
  if(path.startsWith('upd/')&&data&&['wd','as','af'].some(k=>data[k]&&data[k]>T))return new Response('future date',{status:403});
  if(path==='srpm/cut'&&data?.date>day(7))return new Response('future week',{status:403});await st.setJSON(path,data);return Response.json({ok:true})}
 if(req.method==='DELETE'){await st.delete(path);return Response.json({ok:true})}
 return new Response('method',{status:405})};
export const config={path:'/api/db'};
