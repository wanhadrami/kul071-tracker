import {getStore} from '@netlify/blobs';import {role,deny} from './_auth.mjs';
export default async req=>{const st=getStore('kul071-photos');const u=new URL(req.url);
 if(req.method==='GET'){const id=u.pathname.split('/').pop();const r=await st.getWithMetadata(id,{type:'arrayBuffer'});if(!r)return new Response('not found',{status:404});return new Response(r.data,{headers:{'content-type':r.metadata.type||'image/jpeg','cache-control':'public,max-age=31536000'}})}
 if(!role(req))return deny();const buf=await req.arrayBuffer();if(buf.byteLength>15e6)return new Response('too large',{status:413});
 const id=Date.now().toString(36)+Math.random().toString(36).slice(2,8);await st.set(id,buf,{metadata:{type:req.headers.get('content-type')||'image/jpeg'}});
 return Response.json({id,url:'/_blob/'+id,sizeBytes:buf.byteLength})};
export const config={path:['/api/photo','/_blob/*']};
