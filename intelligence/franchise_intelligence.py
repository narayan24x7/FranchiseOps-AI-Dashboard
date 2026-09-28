"""Compatibility mapping for the supplied agents; scoring stays in their modules."""
import hashlib,json
import pandas as pd
from database.store import ROOT
from pipeline import FILES
from src.intelligence_engine import intelligence_engine as engine


def audit_rows(output, frames):
 lookup=frames['data'].drop_duplicates('Outlet_ID').set_index('Outlet_ID')
 rows=[]
 for source in json.loads(output.to_json(orient='records')):
  if not source['Issue_Count']:continue
  oid=source['Outlet_ID'];r=dict(source)
  key='supplied-audit:'+oid+':'+source['Audit_Month']+':'+source['Rules_Failed']
  r.update(Finding_ID=hashlib.sha256(key.encode()).hexdigest()[:24],
   Region=lookup.loc[oid,'Region'] if oid in lookup.index else '',
   Rule=source['Rules_Failed'],Evidence=source['Findings'],
   Recommended_Action=source['Corrective_Actions'],Period=source['Audit_Month'],Status='Open')
  rows.append(r)
 return rows


def build(frames, audit_output):
 """Publish the supplied engine output with aliases used by the existing UI."""
 # Retain original P1-P4 priorities and expose named severity expected by the engine.
 audit_input=audit_output.copy()
 audit_input['Agent_Priority']=audit_input['Severity']
 audit_input.to_csv(engine.AGENT_FILES['audit'],index=False)
 # Adapt current outlet outputs instead of the branch's unrelated sample dataset.
 performance=pd.read_csv(FILES['performance']).rename(columns={
  'Performance_Score':'performance_score','Performance_Category':'health_category'})
 performance['alert_level']='Unknown'
 performance['revenue_growth_pct']=float('nan')
 performance['benchmark_gap_pct']=float('nan')
 performance.to_csv(engine.AGENT_FILES['performance'],index=False)
 pd.read_csv(FILES['staff']).to_csv(engine.AGENT_FILES['staff'],index=False)
 engine.build_intelligence()
 output=pd.read_csv(engine.OUTPUT_FILE)
 # Reuse the supplied preparation functions to expose the same driver values.
 prepared={}
 for name,path in engine.AGENT_FILES.items():
  raw=engine.load_agent(name,path)
  if raw is None:continue
  fn={'performance':engine.prepare_performance,'inventory':engine.prepare_inventory,
      'marketing':engine.prepare_marketing}.get(name)
  d=fn(raw) if fn else engine.prepare_generic_agent(raw,name)
  prepared[name]=d.set_index('Outlet_ID')
 lookup=frames['data'].drop_duplicates('Outlet_ID').set_index('Outlet_ID')
 rows=[]
 for source in json.loads(output.to_json(orient='records')):
  oid=source['Outlet_ID'];r=dict(source)
  for name,alias in [('performance','Performance'),('inventory','Inventory'),('staff','Workforce'),('marketing','Marketing'),('audit','Audit')]:
   d=prepared.get(name);key=name.capitalize()+'_Health'
   value=d.loc[oid,key] if d is not None and oid in d.index else None
   r[alias]=None if value is None or pd.isna(value) else float(value)
  info=lookup.loc[oid] if oid in lookup.index else {}
  r.update(Outlet_Name=info.get('Outlet_Name',oid),Region=info.get('Region',''),City=info.get('City',''),
   Intelligence_Score=source['Health_Score'],Primary_Focus=source['Risk_Areas'],
   Recommended_Action=source['Strategic_Recommendation'])
  rows.append(r)
 return rows
