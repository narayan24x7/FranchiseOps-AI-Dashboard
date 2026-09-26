import threading,uuid,traceback
from database.store import connect,now,save
from pipeline import run as legacy_run
from src.milestone4.data_preparation import prepare
from audit_agent.audit_agent import build as audit
from intelligence.franchise_intelligence import build as intelligence
LOCK=threading.Lock()
STEPS=['Source agents','Data validation','Audit agent','Intelligence engine','Database publication']
def execute(run_id,target):
 try:
  def step(name,status,detail=''):
   with connect() as c:c.execute('UPDATE run_steps SET status=?,detail=? WHERE run_id=? AND name=?',(status,detail,run_id,name))
  step(STEPS[0],'running');legacy_run('all' if target in ['all','milestone4'] else target);step(STEPS[0],'succeeded')
  step(STEPS[1],'running');frames,checks=prepare();step(STEPS[1],'succeeded')
  step(STEPS[2],'running');findings,scores=audit(frames);step(STEPS[2],'succeeded')
  step(STEPS[3],'running');ranked=intelligence(frames,scores);step(STEPS[3],'succeeded')
  step(STEPS[4],'running')
  with connect() as c:
   c.execute('DELETE FROM monthly_sales');c.execute('DELETE FROM outlets')
   d=frames['data'];out=d.drop_duplicates('Outlet_ID')
   c.executemany('INSERT INTO outlets VALUES(?,?,?,?)',out[['Outlet_ID','Outlet_Name','Region','City']].itertuples(index=False,name=None))
   c.executemany('INSERT INTO monthly_sales VALUES(?,?,?,?,?)',d[['Outlet_ID','Month','Sales_Revenue_INR','Profit_INR','Orders']].itertuples(index=False,name=None))
   for name,value in [('audit',findings),('intelligence',ranked),('validation',checks),('summary',dict(rows=len(d),outlets=len(out),months=d.Month.nunique(),latest=d.Month.max(),generated=now(),run_id=run_id))]:save(c,name,value)
  step(STEPS[4],'succeeded')
  with connect() as c:c.execute('UPDATE runs SET status=?,finished=? WHERE id=?',('succeeded',now(),run_id))
 except Exception as e:
  traceback.print_exc()
  with connect() as c:
   c.execute("UPDATE run_steps SET status='failed',detail=? WHERE run_id=? AND status='running'",(str(e),run_id))
   c.execute("UPDATE run_steps SET status='skipped' WHERE run_id=? AND status='pending'",(run_id,))
   c.execute('UPDATE runs SET status=?,finished=?,error=? WHERE id=?',('failed',now(),str(e),run_id))
 finally:LOCK.release()
def start(target='milestone4',background=True):
 from pipeline import REGISTRY
 if target not in {'all','milestone4',*REGISTRY}:raise ValueError('Unknown agent')
 if not LOCK.acquire(blocking=False):raise RuntimeError('A pipeline run is already active')
 id=uuid.uuid4().hex
 try:
  with connect() as c:
   c.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',(id,target,'running',now(),None,None))
   c.executemany('INSERT INTO run_steps VALUES(?,?,?,?)',[(id,s,'pending','') for s in STEPS])
 except Exception:LOCK.release();raise
 if background:threading.Thread(target=execute,args=(id,target),daemon=True).start()
 else:execute(id,target)
 return id
