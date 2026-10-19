# Generate honest public discovery; no auth, agent or payment claims.
from html.parser import HTMLParser
import pathlib,json,hashlib,re
BASE='https://vpspricewatch.com'
class Markdown(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.out=[];self.skip=0;self.main=False;self.href=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='main':self.main=True
  if t in ['script','style','noscript']:self.skip+=1
  if not self.main or self.skip:return
  if t in ['h1','h2','h3','h4']:self.out.append('\n\n'+'#'*int(t[1])+' ')
  elif t in ['p','section','article','table']:self.out.append('\n\n')
  elif t=='li':self.out.append('\n- ')
  elif t=='tr':self.out.append('\n| ')
  elif t=='br':self.out.append('\n')
  elif t=='a':self.href.append(a.get('href',''));self.out.append('[')
 def handle_endtag(self,t):
  if t in ['script','style','noscript']:self.skip=max(0,self.skip-1);return
  if not self.main or self.skip:return
  if t=='main':self.main=False
  elif t=='a' and self.href:
   h=self.href.pop();self.out.append(']('+ (BASE+h if h.startswith('/') else h)+')')
  elif t in ['td','th']:self.out.append(' | ')
  elif t in ['p','h1','h2','h3','h4']:self.out.append('\n\n')
 def handle_data(self,d):
  if self.main and not self.skip:self.out.append(re.sub(r'\s+',' ',d))
 def text(self):return re.sub(r'\n[ \t]*\n(?:[ \t]*\n)+','\n\n',''.join(self.out)).strip()+'\n'
def generate(out):
 out=pathlib.Path(out)
 def write(n,t):p=out/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t,encoding='utf-8')
 pages={};expanded=[]
 for p in sorted(out.rglob('*.html')):
  if p.name=='404.html':continue
  rel=p.relative_to(out).as_posix();url='/' if rel=='index.html' else '/'+(rel[:-10] if rel.endswith('/index.html') else rel[:-5])
  parser=Markdown();parser.feed(p.read_text(encoding='utf-8'));md=parser.text()
  if not md.strip():continue
  name='agent-content/'+hashlib.sha256(url.encode()).hexdigest()[:24]+'.md';write(name,md);pages[url]='/'+name
  expanded.append('Source: '+BASE+url+'\n\n'+md)
 write('llms.txt','# VPS Price Watch\n\nIndependent VPS and hosting price and official-offer reference. Check each page’s review date and official provider terms; displayed offers are not a checkout guarantee.\n\n## Content\n- [Offers](https://vpspricewatch.com/)\n- [Provider comparisons](https://vpspricewatch.com/compare)\n- [Brand offers](https://vpspricewatch.com/coupons/)\n- [Guides](https://vpspricewatch.com/guides/)\n- [All canonical URLs](https://vpspricewatch.com/sitemap.xml)\n- [Expanded content](https://vpspricewatch.com/llms-full.txt)\n\n## Access\nPublic read-only pages need no account or token. Request Accept: text/markdown for a text representation. We do not operate checkout, agent registration, an MCP server or an A2A service.\n')
 write('llms-full.txt','# VPS Price Watch public content\n\nGenerated from current public page bodies; official offer sources and review dates remain attached.\n\n'+'\n\n---\n\n'.join(expanded))
 skill='''---
name: read-official-offers
description: Read published hosting and domain offer evidence from VPS Price Watch.
---
# Read published offers

1. GET https://vpspricewatch.com/sitemap.xml and choose a relevant canonical page.
2. GET that page with Accept: text/markdown, or read its ordinary HTML.
3. Preserve the source URL, Last checked and updated date, eligibility and expiry for each claim.
4. Follow the linked provider official source before making a purchase decision. A recorded page is not a checkout or redemption test.

All operations are anonymous read-only HTTP GET requests. No registration, payment, OAuth credentials, MCP endpoint or A2A endpoint is provided. Do not submit orders on this site.
'''
 write('.well-known/agent-skills/read-official-offers/SKILL.md',skill)
 index={'$schema':'https://schemas.agentskills.io/discovery/0.2.0/schema.json','skills':[{'name':'read-official-offers','type':'skill-md','description':'Read public hosting and domain offer evidence with source and review dates.','url':'/.well-known/agent-skills/read-official-offers/SKILL.md','digest':'sha256:'+hashlib.sha256(skill.encode()).hexdigest()}]}
 write('.well-known/agent-skills/index.json',json.dumps(index,indent=2))
 catalog={'specVersion':'1.0','host':{'displayName':'VPS Price Watch','identifier':'did:web:vpspricewatch.com'},'entries':[{'identifier':'urn:air:vpspricewatch.com:skill:read-official-offers','displayName':'Read published offer evidence','type':'text/markdown','url':BASE+'/.well-known/agent-skills/read-official-offers/SKILL.md','representativeQueries':['Find official offer eligibility and review dates','Read published hosting and domain promotions']} ]}
 write('.well-known/ai-catalog.json',json.dumps(catalog,indent=2))
 robots=(out/'robots.txt').read_text(encoding='utf-8');robots+='\n# Public search and retrieval preferences; no training preference declared.\nUser-agent: *\nAllow: /\nContent-Signal: search=yes, ai-input=yes\nAgentmap: '+BASE+'/.well-known/ai-catalog.json\n';write('robots.txt',robots)
 worker='''const pages = PAGES;
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
'''.replace('PAGES',json.dumps(pages))
 write('_worker.js',worker)
 write('_routes.json',json.dumps({'version':1,'include':['/*'],'exclude':[]}))
 return len(pages)
