// Read-only public content services. No checkout, account data or external fetching.
const ORIGIN='https://vpspricewatch.com';
const SCOPE='content:read';
const json=(data,status=200,headers={})=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store',...headers}});
const error=(name,status=400)=>json({error:name},status);
const enc=new TextEncoder();
const b64=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
const un64=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
async function sign(payload,env){
 const key=await crypto.subtle.importKey('pkcs8',un64(env.AGENT_SIGNING_KEY),{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
 const h=b64(enc.encode(JSON.stringify({alg:'RS256',typ:'JWT',kid:'agent-read-20261019'})));const p=b64(enc.encode(JSON.stringify(payload)));const data=h+'.'+p;
 return data+'.'+b64(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,enc.encode(data)));
}
async function verify(token,env,aud){
 try{
  if(!token||token.length>8192)return null;
  const [h,p,s,...extra]=token.split('.');if(extra.length||!s)return null;
  const header=JSON.parse(new TextDecoder().decode(un64(h)));if(header.alg!=='RS256'||header.kid!=='agent-read-20261019')return null;
  const key=await crypto.subtle.importKey('jwk',env.PUBLIC_JWK,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  if(!await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,un64(s),enc.encode(h+'.'+p)))return null;
  const data=JSON.parse(new TextDecoder().decode(un64(p)));const now=Math.floor(Date.now()/1000);
  return data.iss===ORIGIN&&data.aud===aud&&data.exp>now&&data.iat<=now+30?data:null;
 }catch{return null;}
}
async function content(env,request){const u=new URL('/ai/content.json',request.url);const r=await env.ASSETS.fetch(new Request(u));return await r.json();}
function search(items,query){
 const words=String(query||'').toLowerCase().trim().split(/\s+/).filter(Boolean).slice(0,12);
 return items.filter(x=>words.every(w=>(x.title+' '+x.text).toLowerCase().includes(w))).slice(0,10).map(({text,...x})=>({...x,excerpt:text.slice(0,700)}));
}
async function postJson(request){
 if(Number(request.headers.get('content-length')||0)>16384)throw Error('body_too_large');
 const text=await request.text();if(enc.encode(text).length>16384)throw Error('body_too_large');return JSON.parse(text);
}
const tool={name:'search_published_offers',description:'Search this site’s published hosting and domain offer evidence; read-only, no live checkout verification.',inputSchema:{type:'object',properties:{query:{type:'string',maxLength:200}},required:['query'],additionalProperties:false},annotations:{readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false}};
export async function service(request,env){
 const url=new URL(request.url),path=url.pathname;
 if(!['/oauth/register','/oauth/token','/api/agent/content','/api/content','/api/health','/mcp','/a2a'].includes(path))return null;
 const origin=request.headers.get('Origin');if(origin&&origin!==ORIGIN&&origin!==url.origin)return error('origin_not_allowed',403);
 if(path==='/api/health')return request.method==='GET'?json({status:'ok',mode:'read-only',version:'1.0.0'}):error('method_not_allowed',405);
 if(path==='/oauth/register'){
  if(request.method!=='POST')return error('method_not_allowed',405);
  if(!env.AGENT_SIGNING_KEY)return error('temporarily_unavailable',503);
  let body;try{body=await postJson(request);}catch{return error('invalid_client_metadata');}
  if(body.grant_types&&JSON.stringify(body.grant_types)!=='["client_credentials"]')return error('invalid_client_metadata');
  if(body.scope&&body.scope!==SCOPE)return error('invalid_scope');
  if(body.token_endpoint_auth_method&&body.token_endpoint_auth_method!=='client_secret_post')return error('invalid_client_metadata');
  const id=crypto.randomUUID(),now=Math.floor(Date.now()/1000),exp=now+86400;
  const secret=await sign({iss:ORIGIN,aud:ORIGIN+'/oauth/token',sub:id,iat:now,exp,kind:'client'},env);
  return json({client_id:id,client_secret:secret,client_id_issued_at:now,client_secret_expires_at:exp,grant_types:['client_credentials'],response_types:[],token_endpoint_auth_method:'client_secret_post',scope:SCOPE},201,{'Pragma':'no-cache'});
 }
 if(path==='/oauth/token'){
  if(request.method!=='POST')return error('method_not_allowed',405);
  const text=await request.text();if(text.length>16384)return error('invalid_request');
  const f=new URLSearchParams(text);if(f.get('grant_type')!=='client_credentials')return error('unsupported_grant_type');
  const client=await verify(f.get('client_secret'),env,ORIGIN+'/oauth/token');
  if(!client||client.kind!=='client'||client.sub!==f.get('client_id'))return error('invalid_client',401);
  if(f.get('scope')&&f.get('scope')!==SCOPE)return error('invalid_scope');
  const now=Math.floor(Date.now()/1000);const access=await sign({iss:ORIGIN,aud:ORIGIN,sub:client.sub,iat:now,exp:now+600,scope:SCOPE,kind:'access',jti:crypto.randomUUID()},env);
  return json({access_token:access,token_type:'Bearer',expires_in:600,scope:SCOPE},200,{'Pragma':'no-cache'});
 }
 if(path==='/api/agent/content'){
  if(request.method!=='GET')return error('method_not_allowed',405);
  const token=request.headers.get('Authorization')?.match(/^Bearer (.+)$/i)?.[1];const data=await verify(token,env,ORIGIN);
  if(!data||data.kind!=='access'||data.scope!==SCOPE)return json({error:'invalid_token'},401,{'WWW-Authenticate':'Bearer resource_metadata="'+ORIGIN+'/.well-known/oauth-protected-resource", scope="content:read"'});
  return json({items:search(await content(env,request),url.searchParams.get('q')),scope:SCOPE});
 }
 if(path==='/api/content'){
  if(request.method!=='GET')return error('method_not_allowed',405);
  return json({items:search(await content(env,request),url.searchParams.get('q'))});
 }
 if(request.method!=='POST')return error('method_not_allowed',405);
 if(path==='/mcp'){
  const version=request.headers.get('MCP-Protocol-Version');if(version&&!['2025-06-18','2025-03-26'].includes(version))return error('unsupported_protocol_version');
  let message;try{message=await postJson(request);}catch{return error('invalid_request');}
  if(Array.isArray(message)||message.jsonrpc!=='2.0'||typeof message.method!=='string')return error('invalid_request');
  if(message.id===undefined)return new Response(null,{status:202});
  const reply=result=>json({jsonrpc:'2.0',id:message.id,result});
  const fail=(code,text)=>json({jsonrpc:'2.0',id:message.id,error:{code,message:text}});
  if(message.method==='initialize')return reply({protocolVersion:'2025-06-18',serverInfo:{name:'vps-price-watch-read-only',version:'1.0.0'},capabilities:{tools:{}}});
  if(message.method==='ping')return reply({});
  if(message.method==='tools/list')return reply({tools:[tool]});
  if(message.method==='tools/call'){
   const p=message.params;if(p?.name!==tool.name||typeof p.arguments?.query!=='string'||p.arguments.query.length>200)return fail(-32602,'Invalid read-only tool arguments');
   return reply({content:[{type:'text',text:JSON.stringify(search(await content(env,request),p.arguments.query))}],isError:false});
  }
  return fail(-32601,'Method not found');
 }
 if(path==='/a2a'){
  let m;try{m=await postJson(request);}catch{return error('invalid_request');}
  if(m.jsonrpc!=='2.0'||m.method!=='message/send')return json({jsonrpc:'2.0',id:m.id??null,error:{code:-32601,message:'Only synchronous message/send is supported'}});
  const text=m.params?.message?.parts?.filter(x=>x.kind==='text').map(x=>x.text).join(' ');
  if(!text||text.length>200)return json({jsonrpc:'2.0',id:m.id,error:{code:-32602,message:'Provide a search query of up to 200 characters'}});
  return json({jsonrpc:'2.0',id:m.id,result:{kind:'message',messageId:crypto.randomUUID(),role:'agent',parts:[{kind:'text',text:JSON.stringify(search(await content(env,request),text))}]}});
 }
 return null;
}
