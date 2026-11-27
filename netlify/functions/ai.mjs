import Anthropic from '@anthropic-ai/sdk';import {role,deny} from './_auth.mjs';
export default async req=>{if(!role(req))return deny();const {input}=await req.json();
 let messages=typeof input==='string'?[{role:'user',content:input}]:input;
 messages=messages.reduce((m,x)=>{if(m.length&&m[m.length-1].role===x.role)m[m.length-1].content+='\n\n'+x.content;else m.push({role:x.role,content:String(x.content)});return m},[]);
 try{const client=new Anthropic();const res=await client.messages.create({model:Netlify.env.get('AI_MODEL')||'claude-haiku-5-5',max_tokens:900,messages});
  return Response.json({text:res.content.filter(b=>b.type==='text').map(b=>b.text).join('')})}
 catch(e){return new Response('AI error: '+e.message,{status:502})}};
export const config={path:'/api/ai'};
