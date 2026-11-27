export function role(req){const p=req.headers.get('x-pin')||'';const A=Netlify.env.get('ADMIN_PIN'),T=Netlify.env.get('TEAM_PIN');if(A&&p===A)return'admin';if(T&&p===T)return'team';return null}
export const deny=()=>new Response('PIN required',{status:401});
