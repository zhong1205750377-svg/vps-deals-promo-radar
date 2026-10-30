import {service} from './agent_services.js';
const PUBLIC_JWK={"kty": "RSA", "n": "vY1sJXXP34edS8h8KLZrjCvJ9-SngebuerA1wgwuBRBpaQbY57KwR297o5yiQOEW83KJSiD4Z0VwZaIq4LH2-Uzn0PC3Ur8WlyHxxAfLvj5CFwakl_ckREBQcvPaQS87srTQ5-fK7AzolELWzGjtdtvdabJxQdpKHztxjkG2g8kBmLeKnfiEGJxCEG2g6tndSVOsCtVQ8dT5VDvarG0eLPsPiojib9L5yraHrIx7vOJm6IrzBgYKwmZ3Kn8Nh4KPf-MIGQVlu1Lw9w8RpA7zIAH6et68TLsqqkk1TutytNdqijj0gygWcd5CZirBpabJ2y6pw8L_jH31YkbBJRPEgw", "e": "AQAB", "kid": "agent-read-20261019", "use": "sig", "alg": "RS256"};
const pages = {"/about": "/agent-content/979bddc4a8caafdda41370de.md", "/ai/": "/agent-content/c2505309a11e47ae1d82c203.md", "/compare": "/agent-content/a00971334b056054e1e69d47.md", "/contact": "/agent-content/4eb950636535d637ee743743.md", "/coupons/carrd/": "/agent-content/2e4f9f69a5e2135d161e0241.md", "/coupons/chemicloud/": "/agent-content/880dea9b3a9d16c6da0782d6.md", "/coupons/cloudways/": "/agent-content/66b85e4518f171f47621a9da.md", "/coupons/digitalocean/": "/agent-content/0252882774400cd8e5a20a70.md", "/coupons/dreamhost/": "/agent-content/caf53d6cd68bdd81262a802c.md", "/coupons/gandi/": "/agent-content/af4e4780137f7d13079902be.md", "/coupons/gname/": "/agent-content/d0e13d9239c6739985061353.md", "/coupons/hetzner/": "/agent-content/0ef47c4e67aa70e4724b000a.md", "/coupons/hostinger/": "/agent-content/cece9444f027bf4f1397b520.md", "/coupons/": "/agent-content/8a7ec3fab0c34a1b5b3b2ace.md", "/coupons/inmotion/": "/agent-content/0a042c81f199747cce6e61e2.md", "/coupons/namebright/": "/agent-content/8493fb6b8a3c7d34c31c14cb.md", "/coupons/namecheap/": "/agent-content/f16f09e5b059afce8d4b7291.md", "/coupons/namesilo/": "/agent-content/08718c4a3752bb725ad4dc7a.md", "/coupons/netcup/": "/agent-content/b6bf87b83080783b81d71f07.md", "/coupons/ramnode/": "/agent-content/2d7c65e84b2f6c94c8ca3e7e.md", "/coupons/render/": "/agent-content/b94e0034325e98bd26a37d73.md", "/coupons/siteground/": "/agent-content/2c35ccc8c7dc9cc2de8e76da.md", "/coupons/squarespace/": "/agent-content/635ff0882d1aae58c9d7bbe7.md", "/coupons/vultr/": "/agent-content/848d0eff08e3fc84e327969e.md", "/guides/azure-virtual-server-pricing-source-scope/": "/agent-content/225d1016c293a917f632df95.md", "/guides/azure-vm-pricing-hourly-commitment/": "/agent-content/41caa30ebb7e7a9b6cc05f68.md", "/guides/best-vps-server-cpu-allocation/": "/agent-content/9e173f3b3937a75c0b02139e.md", "/guides/cheap-vps-price-change-evidence/": "/agent-content/9f83df52b9ceb9754e4e208a.md", "/guides/cheap-windows-vps-rdp-access-scope/": "/agent-content/913f8fb7f15779598b86a7ea.md", "/guides/compare-vps-prices-billing-terms/": "/agent-content/376dc07a306588e8228fa497.md", "/guides/hostinger-vps-pricing-refund-clocks/": "/agent-content/706029c6ba28e91aea2cb581.md", "/guides/": "/agent-content/65c77e41e1a7cacb4c0a1c02.md", "/guides/vps-prices-seven-day-backups/": "/agent-content/5afeddf7d273809ae38d5d4d.md", "/guides/vps-server-outbound-transfer-scope/": "/agent-content/58b6d022f329abec6d371bce.md", "/guides/vultr-pricing-stop-destroy-retained-resources/": "/agent-content/99910104879889fc15c2a5d8.md", "/guides/windows-vps-server-license-inclusion/": "/agent-content/862e7c1042060f0913449fca.md", "/": "/agent-content/8a5edab282632443219e051e.md", "/privacy": "/agent-content/0ece7f7c306b4cf686ab5121.md", "/provider-digitalocean": "/agent-content/acef336e1914b4a4dd5a6f71.md", "/provider-hostinger": "/agent-content/51e0d608dae7235600dd8849.md", "/provider-ovhcloud": "/agent-content/ecc18af486d79725de480aba.md"};
const links = '</.well-known/api-catalog>; rel="api-catalog", </llms.txt>; rel="describedby", </.well-known/agent-skills/index.json>; rel="service-doc", </.well-known/ai-catalog.json>; rel="ai-catalog"';
export default { async fetch(request, env) {
 env={...env,PUBLIC_JWK};
 const action=await service(request,env);if(action)return action;
 const url = new URL(request.url);
 let path = url.pathname;
 if(path.endsWith('/index.html')) path=path.slice(0,-10);
 if(path.endsWith('.html')) path=path.slice(0,-5);
 const accept=request.headers.get('Accept')||'';
 const formats=accept.split(',').map(s=>{const [type,...params]=s.trim().split(';');const q=params.find(p=>p.trim().startsWith('q='));return {type,q:q?Number(q.trim().slice(2)):1};});
 const markdownQ=Math.max(0,...formats.filter(x=>x.type==='text/markdown').map(x=>x.q));
 const htmlQ=Math.max(0,...formats.filter(x=>x.type==='text/html').map(x=>x.q));
 const asset=pages[path]||pages[path+'/'];
 if((request.method==='GET'||request.method==='HEAD') && asset && markdownQ>0 && markdownQ>=htmlQ){
  const mdUrl=new URL(asset,url.origin);
  const source=await env.ASSETS.fetch(new Request(mdUrl,{method:'GET'}));
  if(source.ok){const text=await source.text();return new Response(request.method==='HEAD'?null:text,{status:200,headers:{'Content-Type':'text/markdown; charset=utf-8','Vary':'Accept','Link':links,'Cache-Control':'public, max-age=300'}});}
 }
 let original=await env.ASSETS.fetch(request);
 if(original.ok&&(original.headers.get('Content-Type')||'').includes('text/html')&&request.method==='GET'){
  const text=await original.text(); const injected=text.replace('</head>','<script src="/ai/browser-tools.js" defer></script></head>');
  original=new Response(injected,original);original.headers.delete('Content-Length');original.headers.delete('ETag');
 }
 if(path==='/.well-known/api-catalog'){original=new Response(original.body,original);original.headers.set('Content-Type','application/linkset+json');}
 if(path.startsWith('/.well-known/oauth-')){original=new Response(original.body,original);original.headers.set('Content-Type','application/json');}
 if(path==='/ai/index.ilang'){original=new Response(original.body,original);original.headers.set('Content-Type','text/plain; charset=utf-8');}
 const response=new Response(original.body,original);
 response.headers.set('Link',links);
 if(asset)response.headers.set('Vary','Accept');
 if(path.startsWith('/.well-known/')||path.startsWith('/agent-content/')||path==='/llms.txt'||path==='/llms-full.txt')response.headers.set('Access-Control-Allow-Origin','*');
 return response;
}};
