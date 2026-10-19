const pages = {"/about": "/agent-content/979bddc4a8caafdda41370de.md", "/compare": "/agent-content/a00971334b056054e1e69d47.md", "/contact": "/agent-content/4eb950636535d637ee743743.md", "/coupons/cloudways/": "/agent-content/66b85e4518f171f47621a9da.md", "/coupons/digitalocean/": "/agent-content/0252882774400cd8e5a20a70.md", "/coupons/dreamhost/": "/agent-content/caf53d6cd68bdd81262a802c.md", "/coupons/hostinger/": "/agent-content/cece9444f027bf4f1397b520.md", "/coupons/": "/agent-content/8a7ec3fab0c34a1b5b3b2ace.md", "/coupons/namecheap/": "/agent-content/f16f09e5b059afce8d4b7291.md", "/coupons/namesilo/": "/agent-content/08718c4a3752bb725ad4dc7a.md", "/coupons/siteground/": "/agent-content/2c35ccc8c7dc9cc2de8e76da.md", "/coupons/vultr/": "/agent-content/848d0eff08e3fc84e327969e.md", "/guides/azure-virtual-server-pricing-source-scope/": "/agent-content/225d1016c293a917f632df95.md", "/guides/azure-vm-pricing-hourly-commitment/": "/agent-content/41caa30ebb7e7a9b6cc05f68.md", "/guides/best-vps-server-cpu-allocation/": "/agent-content/9e173f3b3937a75c0b02139e.md", "/guides/cheap-vps-price-change-evidence/": "/agent-content/9f83df52b9ceb9754e4e208a.md", "/guides/cheap-windows-vps-rdp-access-scope/": "/agent-content/913f8fb7f15779598b86a7ea.md", "/guides/compare-vps-prices-billing-terms/": "/agent-content/376dc07a306588e8228fa497.md", "/guides/hostinger-vps-pricing-refund-clocks/": "/agent-content/706029c6ba28e91aea2cb581.md", "/guides/": "/agent-content/65c77e41e1a7cacb4c0a1c02.md", "/guides/vps-prices-seven-day-backups/": "/agent-content/5afeddf7d273809ae38d5d4d.md", "/guides/vps-server-outbound-transfer-scope/": "/agent-content/58b6d022f329abec6d371bce.md", "/guides/vultr-pricing-stop-destroy-retained-resources/": "/agent-content/99910104879889fc15c2a5d8.md", "/guides/windows-vps-server-license-inclusion/": "/agent-content/862e7c1042060f0913449fca.md", "/": "/agent-content/8a5edab282632443219e051e.md", "/privacy": "/agent-content/0ece7f7c306b4cf686ab5121.md", "/provider-digitalocean": "/agent-content/acef336e1914b4a4dd5a6f71.md", "/provider-hostinger": "/agent-content/51e0d608dae7235600dd8849.md", "/provider-ovhcloud": "/agent-content/ecc18af486d79725de480aba.md"};
const links = '</llms.txt>; rel="describedby", </.well-known/agent-skills/index.json>; rel="service-doc", </.well-known/ai-catalog.json>; rel="ai-catalog"';
export default { async fetch(request, env) {
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
 const original=await env.ASSETS.fetch(request);
 const response=new Response(original.body,original);
 response.headers.set('Link',links);
 if(asset)response.headers.set('Vary','Accept');
 if(path.startsWith('/.well-known/')||path.startsWith('/agent-content/')||path==='/llms.txt'||path==='/llms-full.txt')response.headers.set('Access-Control-Allow-Origin','*');
 return response;
}};
