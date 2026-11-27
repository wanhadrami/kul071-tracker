export function role(req){const p=req.headers.get('x-pin')||'';const A=Netlify.env.get('ADMIN_PIN'),T=Netlify.env.get('TEAM_PIN');
 if(A&&p===A)return'admin';if(T)return p===T?'team':null;return A?'team':'admin'}
export const deny=()=>new Response('PIN required',{status:401});
