import json
from pathlib import Path
import pytest
from app import app
from database.store import connect,snapshot
from src.milestone4.data_preparation import prepare
from intelligence.franchise_intelligence import build
from audit_agent.audit_agent import audit_outlet

def test_complete_snapshot_and_scores():
 frames,checks=prepare()
 assert all(c['Status'] in {'Passed', 'Warning'} for c in checks)
 rows=snapshot('intelligence')
 assert len(rows)==frames['data'].Outlet_ID.nunique()==750
 assert len({r['Outlet_ID'] for r in rows})==len(rows)
 assert all(0<=r['Intelligence_Score']<=100 for r in rows)
 assert all(r['Intelligence_Score']==r['Health_Score'] for r in rows)
 assert all(r['Recommended_Action']==r['Strategic_Recommendation'] for r in rows)
 assert all(r['Issue_Count']>0 for r in snapshot('audit'))


def test_reject_duplicate_sales(monkeypatch):
 import src.milestone4.data_preparation as module
 original=module.pd.read_csv
 def read(path,*args,**kwargs):
  df=original(path,*args,**kwargs)
  if str(path).endswith('milestone1_clean_data.csv'):df=module.pd.concat([df,df.iloc[:1]])
  return df
 monkeypatch.setattr(module.pd,'read_csv',read)
 with pytest.raises(ValueError,match='Unique outlet'):prepare()

def test_snapshot_transaction_rollback():
 with connect() as c:before=c.execute('SELECT count(*) FROM monthly_sales').fetchone()[0]
 with pytest.raises(RuntimeError):
  with connect() as c:
   c.execute('DELETE FROM monthly_sales');raise RuntimeError('Simulated failure')
 with connect() as c:assert c.execute('SELECT count(*) FROM monthly_sales').fetchone()[0]==before

def test_api_contract_and_followup(tmp_path,monkeypatch):
 import shutil
 from database.store import ROOT
 shutil.copy(ROOT/'runtime/franchiseops.db',tmp_path/'franchiseops.db')
 monkeypatch.setenv('FRANCHISEOPS_DATA_DIR',str(tmp_path))
 c=app.test_client()
 assert c.get('/api/m4/summary').json['outlets']==750
 assert c.get('/api/jobs/missing').status_code==404
 assert c.post('/api/run/unknown').status_code==400
 assert c.get('/api/m4/unknown').status_code==404
 finding=c.get('/api/m4/audit').json[0]['Finding_ID']
 assert c.post('/api/findings/'+finding,json={'status':'Resolved','owner':'Test owner','note':'Verified'}).status_code==200
 assert next(r for r in c.get('/api/m4/audit').json if r['Finding_ID']==finding)['Status']=='Resolved'
 assert c.post('/api/findings/'+finding,json={'status':'invalid'}).status_code==400

def test_export_chunks_are_complete_and_below_limit():
 from pipeline import OUT,REGISTRY
 for key in REGISTRY:
  p=OUT/(key+'.json');source=json.loads(p.read_text())
  assert p.stat().st_size<10*1024*1024
  if isinstance(source,dict):
   chunks=[OUT/name for name in source['chunks']]
   assert sum(len(json.loads(p.read_text())) for p in chunks)==source['rows']
   assert all(p.stat().st_size<10*1024*1024 for p in chunks)

def test_orchestration_failure_preserves_snapshot(tmp_path,monkeypatch):
 import shutil
 import orchestration.orchestrator as engine
 from database.store import ROOT
 shutil.copy(ROOT/'runtime/franchiseops.db',tmp_path/'franchiseops.db')
 monkeypatch.setenv('FRANCHISEOPS_DATA_DIR',str(tmp_path))
 before=snapshot('summary')
 def fail(*args):raise ValueError('Injected source failure')
 monkeypatch.setattr(engine,'legacy_run',fail)
 id=engine.start(background=False)
 with connect() as c:
  assert c.execute('SELECT status FROM runs WHERE id=?',(id,)).fetchone()[0]=='failed'
  stages=list(c.execute('SELECT status FROM run_steps WHERE run_id=? ORDER BY rowid',(id,)))
  assert [r[0] for r in stages]==['failed','skipped','skipped','skipped','skipped']
 assert snapshot('summary')==before
 assert not engine.LOCK.locked()

def test_action_center_persists_intelligence_followup(tmp_path,monkeypatch):
 import shutil
 from database.store import ROOT
 shutil.copy(ROOT/'runtime/franchiseops.db',tmp_path/'franchiseops.db')
 monkeypatch.setenv('FRANCHISEOPS_DATA_DIR',str(tmp_path))
 client=app.test_client()
 rows=client.get('/api/actions').json
 assert len(rows)==len(snapshot('audit'))+len(snapshot('intelligence'))
 item=next(r for r in rows if r['Action_ID'].startswith('intelligence:'))
 url='/api/findings/'+item['Action_ID']
 assert client.post(url,json={'status':'In progress','owner':'Outlet lead','note':'Review stock orders'}).status_code==200
 saved=next(r for r in client.get('/api/actions').json if r['Action_ID']==item['Action_ID'])
 assert (saved['Status'],saved['Owner'],saved['Note'])==('In progress','Outlet lead','Review stock orders')
 assert client.post(url,json={'status':'Open','owner':123}).status_code==400
 assert client.post(url,json=['invalid']).status_code==400
 assert client.post('/api/findings/unknown',json={'status':'Open'}).status_code==404
