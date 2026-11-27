import {role,deny} from './_auth.mjs';
export default async req=>{const r=role(req);return r?Response.json({role:r}):deny()};
export const config={path:'/api/whoami'};
