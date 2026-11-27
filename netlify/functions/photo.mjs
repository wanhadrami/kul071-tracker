import {getStore} from '@netlify/blobs';import {role,deny} from './_auth.mjs';
// Large files (e.g. SRP master ~14 MB) go up and down in <=4 MB parts because Netlify functions cap bodies at 6 MB.
export default async req=>{const st=getStore('kul071-photos');const u=new URL(req.url);
 if(req.method==='GET'){const id=u.pathname.split('/').pop(),part=u.searchParams.get('part');
  if(part!=null){const b=await st.get(id+'~'+(+part),{type:'arrayBuffer'});return b?new Response(b,{headers:{'content-type':'application/octet-stream','cache-control':'public,max-age=31536000'}}):new Response('not found',{status:404})}
  const r=await st.getWithMetadata(id,{type:'arrayBuffer'});if(!r)return new Response('not found',{status:404});
  if(r.metadata.parts)return Response.json({parts:r.metadata.parts,type:r.metadata.type},{headers:{'x-parts':String(r.metadata.parts)}});
  return new Response(r.data,{headers:{'content-type':r.metadata.type||'image/jpeg','cache-control':'public,max-age=31536000'}})}
 if(!role(req))return deny();const buf=await req.arrayBuffer();if(buf.byteLength>5e6)return new Response('too large',{status:413});
 const type=req.headers.get('content-type')||'image/jpeg',ch=u.searchParams.get('chunk');
 if(ch!=null){const i=+ch,n=+u.searchParams.get('of'),id=u.searchParams.get('id')||(Date.now().toString(36)+Math.random().toString(36).slice(2,8));
  if(!/^[a-z0-9]+$/.test(id)||!(n>0&&n<=20&&i>=0&&i<n))return new Response('bad chunk',{status:400});
  await st.set(id+'~'+i,buf);if(i===n-1)await st.set(id,new ArrayBuffer(0),{metadata:{type,parts:n}});
  return Response.json({id,url:'/_blob/'+id,done:i===n-1})}
 const id=Date.now().toString(36)+Math.random().toString(36).slice(2,8);await st.set(id,buf,{metadata:{type}});
 return Response.json({id,url:'/_blob/'+id,sizeBytes:buf.byteLength})};
export const config={path:['/api/photo','/_blob/*']};
