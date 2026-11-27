"""QA regression harness for KUL071 tracker (isolated: local files, in-memory DB, no network).
Run: python3 -I tests/qa.py   (from repo root; needs playwright + openpyxl)"""
import asyncio,json,io,base64,sys,os,copy
from playwright.async_api import async_playwright
import openpyxl
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSZIP='/opt/node-tools/node_modules/jszip/dist/jszip.min.js'
XER=os.environ.get('QA_XER','')            # optional real 25 Nov XER for T03
HTML=open(os.path.join(ROOT,'index.html')).read().replace("let dR='',","window.__t=c=>eval(c);let dR='',",1)
SHEETS=['GF - ACMV','GF - Electrical Works','FF - ACMV','1F - Electrical Works ']
R=[]
def rec(t,name,ok,detail): R.append((t,name,ok,detail));print(('PASS ' if ok else 'FAIL ')+t+' '+name+' :: '+detail)

class Store:
  def __init__(s):s.d={};s.fail=set();s.blobs={}
  async def handle(s,route):
    q=route.request;u=q.url
    if u.endswith('/') or u.split('?')[0].endswith('/index.html'):return await route.fulfill(body=HTML,content_type='text/html')
    for f in ['shim.js','baseline.json','b1.json','pmx-logo.png']:
      if f in u.split('/')[-1]:return await route.fulfill(path=os.path.join(ROOT,f))
    if 'jszip' in u:return await route.fulfill(path=JSZIP,content_type='text/javascript')
    if '/api/whoami' in u:return await route.fulfill(body='{"role":"admin"}',content_type='application/json')
    if '/_blob/' in u:
      k=u.split('/_blob/')[1];return await route.fulfill(body=s.blobs.get(k,b''),content_type='application/octet-stream')
    if '/api/db' in u:
      if q.method=='GET':return await route.fulfill(body=json.dumps(s.d),content_type='application/json')
      if q.method=='PUT':
        b=json.loads(q.post_data);
        if any(b['path'].startswith(p) for p in s.fail):return await route.fulfill(status=500,body='fail')
        s.d[b['path']]=b['data'];return await route.fulfill(body='{"ok":true}',content_type='application/json')
      if q.method=='DELETE':
        p=u.split('path=')[1];import urllib.parse;p=urllib.parse.unquote(p)
        if any(p.startswith(x) for x in s.fail):return await route.fulfill(status=500,body='fail')
        s.d.pop(p,None);return await route.fulfill(body='{"ok":true}',content_type='application/json')
    if '/api/photo' in u and q.method=='POST':
      k='u%d'%len(s.blobs);s.blobs[k]=q.post_data_buffer;return await route.fulfill(body=json.dumps({'id':k,'url':'/_blob/'+k}),content_type='application/json')
    if '/api/' in u:return await route.fulfill(body='{}',content_type='application/json')
    return await route.abort()

async def page(br,st):
  ctx=await br.new_context(viewport={'width':390,'height':844});pg=await ctx.new_page()
  pg.errs=[];pg.on('pageerror',lambda e:pg.errs.append(str(e)))
  await pg.route('**/*',st.handle);await pg.goto('http://qa.test/');await pg.wait_for_timeout(1500)
  if await pg.query_selector('input[name=n]'):
    await pg.fill('input[name=n]','QA');await pg.click('form button');await pg.wait_for_timeout(1200)
  await pg.evaluate("__t(`if(typeof tour!=='undefined'&&tour)endTour();document.querySelectorAll('#onb,#tour').forEach(e=>e.classList.remove('on'))`)")
  return pg
J=lambda pg,c:pg.evaluate("c=>__t(c)",c)
async def JA(pg,c):return await pg.evaluate("async c=>await __t('(async()=>{'+c+'})()')",c)

def xlsx(cells):  # cells: {sheet:{ref:val}}
  wb=openpyxl.Workbook();wb.remove(wb.active)
  for sh,m in cells.items():
    ws=wb.create_sheet(sh)
    for k,v in m.items():ws[k]=v
  b=io.BytesIO();wb.save(b);return b.getvalue()
def readx(b):
  wb=openpyxl.load_workbook(io.BytesIO(b),data_only=False);return wb

async def main():
  async with async_playwright() as p:
    br=await p.chromium.launch()
    # ---------------- T01 W75 regeneration ----------------
    st=Store();pg=await page(br,st)
    info=await JA(pg,"""sCut='2026-11-25';const W0=sWeek(sCut);const sv=SWK[W0];
      const rows=SRP.flatMap(s=>s.rows.map(([r])=>[s.k+r,s.name,r]));
      return {W0,saved:sv?wPh(sv)*100:null,draft:avg(SIDS.map(id=>sPh(sFinal(id))))*100,prev:wPh(SWK[W0-1])*100,rows,sv:sv&&sv.v,scol:SCOL}""")
    rec('T01','draft equals saved W75 on open',abs(info['draft']-info['saved'])<0.005,f"saved {info['saved']:.2f}% · draft {info['draft']:.2f}% · W74 {info['prev']:.2f}%")
    # master = saved W75 values -> unchanged re-export must preserve every mapped cell
    cells={sh:{} for sh in SHEETS}
    for id,name,r in info['rows']:
      for i,c in enumerate(info['scol']['p']):cells[name][f'{c}{r}']=info['sv'][id][i]
    st.blobs['m1']=xlsx(cells)
    out=await JA(pg,"""SM={id:'m1',name:'master.xlsx'};let got=null;dl={save:async o=>{got=o}};const before=JSON.stringify(SG[sWeek(sCut)]||null);
      await sGenerate();await new Promise(r=>setTimeout(r,800));if(got&&got.data){const a=new Uint8Array(await got.data.arrayBuffer());let s='';a.forEach(x=>s+=String.fromCharCode(x));return {b64:btoa(s),hist:!!SG[sWeek(sCut)]}}return {b64:null,hist:!!SG[sWeek(sCut)],panel:!!document.querySelector('.sdf')}""")
    if out['b64']:
      wb=readx(base64.b64decode(out['b64']));ch=[]
      for id,name,r in info['rows']:
        for i,c in enumerate(info['scol']['p']):
          v=wb[name][f'{c}{r}'].value;m=info['sv'][id][i]
          if v is None or abs(float(v)-m)>1e-6:ch.append(f"{name.strip()}!{c}{r} {m}->{v}")
      rec('T01','unchanged re-export preserves mapped cells',not ch,f"{len(ch)} changed"+(': '+'; '.join(ch[:6]) if ch else ''))
    else:rec('T01','unchanged re-export preserves mapped cells',False,'no file produced'+(' (diff panel shown)' if out.get('panel') else ''))
    # master differs from saved -> must show differences before writing
    cells2=copy.deepcopy(cells);cells2['GF - ACMV']['AB21']=0.95
    st.blobs['m2']=xlsx(cells2)
    out2=await JA(pg,"""SM={id:'m2',name:'master2.xlsx'};let got=null;dl={save:async o=>{got=o}};delete SG[sWeek(sCut)];sMerge();
      await sGenerate();await new Promise(r=>setTimeout(r,600));return {file:!!got,panel:document.querySelector('.sdf')?.innerText||''}""")
    rec('T01','master vs app differences shown before generation',(not out2['file']) and 'AB21' in out2['panel'],f"file written={out2['file']} · panel={out2['panel'][:80]!r}")
    # cut-off validation
    c=await JA(pg,"""const i=document.createElement('input');i.id='sCut';i.value='2026-11-27';document.body.appendChild(i);i.dispatchEvent(new Event('change',{bubbles:true}));i.remove();return sCut""")
    rec('T01','cut-off snaps to Wednesday',c=='2026-12-02',f"picked Fri 27 Nov -> {c}")
    # ---------------- T02 wrong workbook ----------------
    st.blobs['bad']=xlsx({'Unrelated':{'A1':1}})
    o=await JA(pg,"""sCut='2026-12-02';const W0=sWeek(sCut);delete SG[W0];sMerge();SM={id:'bad',name:'bad.xlsx'};let got=null;dl={save:async o=>{got=o}};
      await sGenerate();await new Promise(r=>setTimeout(r,500));return {file:!!got,hist:!!SG[W0],stored:!!(window.__x=1)}""")
    rec('T02','incompatible workbook does not finalise week',not o['file'] and not o['hist'] and not any(k.startswith('srpg/W076') for k in st.d),f"file={o['file']} history={o['hist']} stored={[k for k in st.d if k.startswith('srpg')]}")
    await pg.context.close()
    # ---------------- T03 older XER ----------------
    if XER:
      st=Store();pg=await page(br,st);txt=open(XER,encoding='cp1252').read()
      await pg.evaluate("t=>window.__x25=t",txt);await pg.evaluate("t=>window.__x18=t",txt.replace('2026-11-25 17:00','2026-11-18 17:00'))
      await JA(pg,"await importXer(new File([window.__x25],'25.xer'));")
      r=await JA(pg,"""const a=A.find(x=>x.id==='ROMP4-3480');const f={...eff(a),...pick(U[sid(a.id)])};f.st='C';f.pct=100;f.as=f.as||'2026-11-20';f.af=today();await save(a,f,true);
        const p1=A.filter(pend).map(x=>x.id);await importXer(new File([window.__x18],'18.xer'));return {p1,dd:B.dd,p2:A.filter(pend).map(x=>x.id),doc:!!U[sid('ROMP4-3480')]}""")
      rec('T03','older XER keeps unresolved site update pending','ROMP4-3480' in r['p2'] and r['dd']=='2026-11-25',f"before {r['p1']} · after import data date {r['dd']} pending {r['p2']} · doc exists {r['doc']}")
      r2=await JA(pg,"""await importXer(new File([window.__x25],'25b.xer'));return A.filter(pend).map(x=>x.id)""")
      rec('T03','same-date reload keeps unmatched update pending','ROMP4-3480' in r2,f"pending after same-date reload {r2}")
      r3=await JA(pg,"""const nb=JSON.parse(JSON.stringify(B));nb.dd='2026-12-02';nb.at=Date.now();const x=nb.acts.find(a=>a.id==='ROMP4-3480');x.st='C';x.pct=100;x.af='2026-11-27';x.as=x.as||'2026-11-20';setBase(nb);return A.filter(pend).map(a=>a.id)""")
      rec('T03','newer XER containing the update reconciles it','ROMP4-3480' not in r3,f"pending after reconciled XER {r3}")
      await pg.context.close()
    else:rec('T03','older XER',False,'set QA_XER to the 25 Nov XER to run')
    # ---------------- T04 per-week overrides ----------------
    st=Store();pg=await page(br,st)
    r=await JA(pg,"""sCut='2026-11-25';sTmp={id:'gfa21',k:1,v:.93,sg:null};await sSaveCell();sCut='2026-12-02';sTmp={id:'gfa21',k:1,v:.96,sg:null};await sSaveCell();
      const w76=sFinal('gfa21')[1];sCut='2026-11-25';return {w75:sFinal('gfa21')[1],w76}""")
    await pg.reload();await pg.wait_for_timeout(1500)
    r2=await JA(pg,"""sCut='2026-11-25';const a=sFinal('gfa21')[1];sCut='2026-12-02';return {w75:a,w76:sFinal('gfa21')[1]}""")
    rec('T04','W75 and W76 overrides independent (incl. reload)',abs(r['w75']-.93)<1e-9 and abs(r['w76']-.96)<1e-9 and abs(r2['w75']-.93)<1e-9 and abs(r2['w76']-.96)<1e-9,f"live W75 {r['w75']} W76 {r['w76']} · after reload W75 {r2['w75']} W76 {r2['w76']}")
    # ---------------- T05 failed save ----------------
    st.fail.add('srpo/')
    r=await JA(pg,"""sCut='2026-12-02';sTmp={id:'gfa21',k:1,v:.99,sg:null};await sSaveCell();await new Promise(r=>setTimeout(r,300));return sFinal('gfa21')[1]""")
    stored=[v for k,v in st.d.items() if k.startswith('srpo/') and 'gfa21' in k]
    rec('T05','failed SRP save reverts displayed value',abs(r-.96)<1e-9,f"screen {r} · stored {[s['v'][1] for s in stored]}")
    r=await JA(pg,"""const id='gfe20';const before=sFinal(id).slice();sCut='2026-12-02';const a=A.find(a=>sActs(id).includes(a)&&isOpen(a));U[sid(a.id)]={id:a.id,st:'A',pct:99,pat:Date.now()};
      const n=sPendAll().length;await sAcceptAll();await new Promise(r=>setTimeout(r,300));return {n,after:sPendAll().length,same:JSON.stringify(sFinal(id))===JSON.stringify(before)}""")
    rec('T05','failed Accept all reverts',r['after']==r['n'] and r['same'],f"pending before {r['n']} after {r['after']} · values unchanged {r['same']}")
    st.fail.clear();await pg.context.close()
    # ---------------- T06 concurrent edits ----------------
    st=Store();A_=await page(br,st);B_=await page(br,st)
    await J(B_,"window.__old=(()=>{const a=A.find(x=>x.id==='ROMP4-3460');return {...eff(a),...pick(U[sid(a.id)])}})()")
    await JA(A_,"""const a=A.find(x=>x.id==='ROMP4-3460');const f={...eff(a),...pick(U[sid(a.id)])};f.cons='Material not on site';f.cown='Supplier';await save(a,f,true)""")
    await JA(B_,"""const a=A.find(x=>x.id==='ROMP4-3460');const f={...window.__old};f.rm='Checked with foreman';await save(a,f,true)""")
    d=st.d.get('upd/ROMP4-3460',{})
    rec('T06','disjoint edits both preserved',d.get('cons')=='Material not on site' and d.get('rm')=='Checked with foreman',f"stored cons={d.get('cons')!r} rm={d.get('rm')!r}")
    errs=A_.errs+B_.errs
    await br.close()
  print('\nSUMMARY',sum(1 for r in R if r[2]),'/',len(R),'passed');json.dump(R,open('/tmp/qa_results.json','w'))
if __name__=='__main__':asyncio.run(main())
