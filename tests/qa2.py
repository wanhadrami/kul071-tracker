"""Regression tests T07-T12: XER reconciliation (all fields) and SRP master validation at upload.
Run: QA_XER=<25 Nov XER> python3 -I tests/qa2.py"""
import asyncio,json,base64,os,sys,random
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from qa import Store,page,J,JA,xlsx,readx,SHEETS,rec,R
from playwright.async_api import async_playwright
XER=os.environ['QA_XER'];BASE=open(XER,encoding='cp1252').read()
def xer(dd='2026-12-02 17:00',edit=None,drop=None):
  out=[];hdr=None;intask=False
  for ln in BASE.split('\n'):
    c=ln.rstrip('\r').split('\t')
    if c[0]=='%T':intask=c[1]=='TASK'
    if intask and c[0]=='%F':hdr=c[1:]
    if intask and c[0]=='%R':
      r=dict(zip(hdr,c[1:]))
      if drop and r['task_code']==drop:continue
      if edit and r['task_code'] in edit:
        r.update(edit[r['task_code']]);ln='%R\t'+'\t'.join(r.get(h,'') for h in hdr)
    out.append(ln)
  return '\n'.join(out).replace('2026-11-25 17:00',dd) if dd else '\n'.join(out)
STUB="""window.XLSX={utils:{encode_cell:({r,c})=>String.fromCharCode(65+c)+(r+1),encode_range:()=>'',aoa_to_sheet:a=>({aoa:a}),book_new:()=>({S:{}}),book_append_sheet:(wb,ws,n)=>wb.S[n]=ws},write:wb=>{window.__wb=wb;return new Uint8Array(1)}};dl={save:async()=>{}};"""
async def load(pg,txt,name):await pg.evaluate("t=>window.__xt=t",txt);return await JA(pg,f"await importXer(new File([window.__xt],'{name}'));return B.dd")
async def pend(pg):return await JA(pg,"return A.filter(pend).map(a=>a.id)")
async def main():
  async with async_playwright() as p:
    br=await p.chromium.launch()
    # T07 site 94% vs new XER 95%
    st=Store();pg=await page(br,st);await load(pg,BASE,'25.xer')
    await JA(pg,"const a=A.find(x=>x.id==='ROMP4-3460');const f={...eff(a),...pick(U[sid(a.id)])};f.st='A';f.pct=94;await save(a,f,true)")
    dd=await load(pg,xer('2026-12-02 17:00'),'dec02.xer');p1=await pend(pg)
    await pg.reload();await pg.wait_for_timeout(1500)
    st.d['base/current'] and None
    p2=await pend(pg);await JA(pg,"goTab('sync')");await pg.wait_for_timeout(600)
    txt=await JA(pg,"return document.querySelector('#s-sync').innerText")
    await J(pg,STUB);await JA(pg,"exportP6()");await pg.wait_for_timeout(300)
    rows=await JA(pg,"if(!window.__wb)return [];const w=window.__wb.S.TASK;return Object.keys(w).filter(k=>/^A\\d+$/.test(k)).map(k=>{const r=k.slice(1);return [w['A'+r]?.v,w['B'+r]?.v,w['E'+r]?.v??null,w['F'+r]?.v??null]})")
    ok='ROMP4-3460' in p1 and 'ROMP4-3460' in p2 and 'P6 95% → Site 94%' in txt and any(r[0]=='ROMP4-3460' for r in rows)
    rec('T07','site 94% vs new XER 95% stays pending (refresh + export)',ok,f"XER dd {dd} · pending live {p1} · after refresh {p2} · sync shows 'P6 95% → Site 94%' {'P6 95% → Site 94%' in txt} · export row {[r for r in rows if r[0]=='ROMP4-3460']}")
    # T08 next XER at 94% (remaining 0.7d) and other fields equal
    await load(pg,xer('2026-12-09 17:00',edit={'ROMP4-3460':{'remain_drtn_hr_cnt':'5.6'}}),'dec09.xer');p3=await pend(pg)
    rec('T08','XER now 94% and all fields match → leaves pending','ROMP4-3460' not in p3,f"pending {p3}")
    await pg.context.close()
    # T09 same progress, actual finish differs
    st=Store();pg=await page(br,st);await load(pg,BASE,'25.xer')
    await JA(pg,"const a=A.find(x=>x.id==='ROMP4-3460');const f={...eff(a),...pick(U[sid(a.id)])};f.st='C';f.pct=100;f.af='2026-11-27';await save(a,f,true)")
    await load(pg,xer('2026-12-02 17:00',edit={'ROMP4-3460':{'status_code':'TK_Complete','act_end_date':'2026-11-26 17:00','remain_drtn_hr_cnt':'0'}}),'fin.xer')
    p4=await pend(pg);await JA(pg,"goTab('sync')");await pg.wait_for_timeout(500);t4=await JA(pg,"return document.querySelector('#s-sync').innerText")
    rec('T09','same progress, different actual finish stays pending + date shown','ROMP4-3460' in p4 and 'Finish P6 26/11/26 → Site 27/11/26' in t4,f"pending {p4} · shows finish diff {'Finish P6 26/11/26 → Site 27/11/26' in t4}")
    # T10 pending ID missing from new XER
    await load(pg,xer('2026-12-09 17:00',drop='ROMP4-3460'),'drop.xer');await JA(pg,"goTab('home');goTab('sync')");await pg.wait_for_timeout(500)
    t5=await JA(pg,"return document.querySelector('#s-sync').innerText")
    rec('T10','pending ID missing from XER flagged for review','Needs review' in t5 and 'ROMP4-3460' in t5,f"'Needs review' shown {'Needs review' in t5} · lists ROMP4-3460 {'ROMP4-3460' in t5}")
    await pg.context.close()
    # T11 wrong.xlsx after a valid master
    st=Store();pg=await page(br,st)
    info=await JA(pg,"sCut='2026-11-25';return {rows:SRP.flatMap(s=>s.rows.map(([r])=>[s.k+r,s.name,r])),sv:SWK[75].v,scol:SCOL}")
    good={sh:{} for sh in SHEETS}
    for id,name,r in info['rows']:
      for i,c in enumerate(info['scol']['p']):good[name][f'{c}{r}']=info['sv'][id][i]
    gb=xlsx(good);bad=xlsx({'Unrelated':{'A1':1}})
    async def upload(b,name):
      await pg.evaluate("([b,n])=>{const a=Uint8Array.from(atob(b),c=>c.charCodeAt(0));window.__f=new File([a],n,{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})}",[base64.b64encode(b).decode(),name])
      await JA(pg,"await sUploadMaster(window.__f)")
    await upload(gb,'PMX master.xlsx');sm1=await JA(pg,"return SM.name");h0=await JA(pg,"return JSON.stringify(SG[75]||null)")
    await upload(bad,'wrong.xlsx');sm2=await JA(pg,"return SM.name");panel=await JA(pg,"return document.querySelector('.sdf')?.innerText||''")
    g=await JA(pg,"let got=null;dl={save:async o=>{got=o}};await sGenerate();await new Promise(r=>setTimeout(r,500));return {file:!!got,hist:!!SG[75],rev:(SG[75]?.rev||[]).length}")
    rec('T11','wrong.xlsx rejected at upload, original master still generates',sm1=='PMX master.xlsx' and sm2=='PMX master.xlsx' and 'Missing sheet' in panel and g['file'] and g['hist'],f"master before {sm1!r} after {sm2!r} · panel {panel[:70]!r} · generate with original: file={g['file']} history={g['hist']}")
    # T12 master differs everywhere → Use master values → output = master, 0 changed; % by tracker formula
    random.seed(7);mast={sh:{} for sh in SHEETS};mv={}
    for id,name,r in info['rows']:
      for i,c in enumerate(info['scol']['p']):v=round(random.choice([0,.1,.25,.4,.6,.75,.85,.93,1]),3);mast[name][f'{c}{r}']=v;mv.setdefault(id,[0,0,0])[i]=v
    await upload(xlsx(mast),'master 25 Nov (synthetic).xlsx')
    d1=await JA(pg,"let got=null;dl={save:async o=>{got=o}};await sGenerate();await new Promise(r=>setTimeout(r,400));return {file:!!got,n:sDiff?.items?.length||0}")
    await JA(pg,"document.querySelector('[data-sdm]')?.click()");await pg.wait_for_timeout(800)
    out=await JA(pg,"let got=null;dl={save:async o=>{got=o}};await sGenerate();await new Promise(r=>setTimeout(r,800));const a=new Uint8Array(await got.data.arrayBuffer());let s='';a.forEach(x=>s+=String.fromCharCode(x));return {b64:btoa(s),pct:avg(SIDS.map(id=>sPh(sFinal(id))))*100}")
    wb=readx(base64.b64decode(out['b64']));ch=[];n=0
    for id,name,r in info['rows']:
      for i,c in enumerate(info['scol']['p']):
        n+=1;v=wb[name][f'{c}{r}'].value
        if v is None or abs(float(v)-mv[id][i])>1e-6:ch.append(f'{name.strip()}!{c}{r}')
    W=[.5,.3,.2];exp=sum(sum(mv[id][i]*W[i] for i in range(3)) for id in mv)/len(mv)*100
    rec('T12','Use master values → 42 inputs unchanged, % = master by tracker formula',n==42 and not ch and abs(out['pct']-exp)<.005,f"diff panel listed {d1['n']} cells, no file first ({not d1['file']}) · compared {n} cells, changed {len(ch)} · app {out['pct']:.2f}% vs master formula {exp:.2f}%")
    # T13 cancel site update after its SRP suggestion was accepted -> SRP back to original; manual value kept
    st=Store();pg=await page(br,st)
    r=await JA(pg,"""sCut=nextWed2();const id='gfe20';const orig=sFinal(id).slice();const acts=sActs(id).filter(isOpen);const a=acts[0];
      const f={...eff(a),...pick(U[sid(a.id)])};f.st='A';f.pct=100;await save(a,f,true);const pend=sPendAll().filter(x=>x[0]===id);await sAcceptAll();const acc=sFinal(id).slice();
      sTmp={id:'gfa21',k:2,v:.95,sg:null};await sSaveCell();
      oItem=a.id;document.body.insertAdjacentHTML('beforeend','<button id=qq data-qrst=1></button>');await new Promise(r=>setTimeout(r,50));
      const k=sid(a.id),old=U[k];delete U[k];if(db)await db.doc('upd/'+k).delete();const nr=await srpRevertOrphans();
      return {orig,acc,after:sFinal(id),nr,manual:sFinal('gfa21')[2],pend:pend.length,act:a.id}""")
    ok=r['acc']!=r['orig'] and all(abs(x-y)<1e-9 for x,y in zip(r['after'],r['orig'])) and abs(r['manual']-.95)<1e-9
    rec('T13','cancelled site update reverts its accepted SRP value (manual kept)',ok,f"{r['act']} → GF ELE row 20: original {r['orig']} · after accept {r['acc']} · after cancel {r['after']} ({r['nr']} cell reverted) · manual GF ACMV Dahu07 3rd stays {r['manual']}")
    r2=await JA(pg,"""const id='gfe20';const a=sActs(id).filter(isOpen)[0];const f={...eff(a),...pick(U[sid(a.id)])};f.st='A';f.pct=100;await save(a,f,true);await sAcceptAll();
      const acc=sFinal(id).slice();await pg_reset(a.id);return {acc,after:sFinal(id)}""".replace('await pg_reset(a.id);',"startRoom(a.area);oItem=a.id;qPanel='rst';renderHome(false);document.querySelector('[data-qrst=\"1\"]').click();await new Promise(r=>setTimeout(r,800));"))
    rec('T13','same via Reset button in Site Walk UI',r2['acc']!=r2['after'],f"after accept {r2['acc']} · after tapping Reset {r2['after']}")
    await br.close()
  print('\nSUMMARY',sum(1 for r in R if r[2]),'/',len(R));json.dump(R,open(os.environ.get('QA_OUT','/tmp/qa2.json'),'w'))
asyncio.run(main())
