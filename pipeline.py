"""Independent, dependency-aware adapters for the uploaded Python agents."""
from pathlib import Path
import sys,json,subprocess,time,os
from datetime import datetime,timezone
import pandas as pd
ROOT=Path(__file__).resolve().parent
E=ROOT
sys.path.insert(0,str(E))
OUT=ROOT/'dashboard/static/data';OUT.mkdir(parents=True,exist_ok=True)
P=E/'data/processed'
REGISTRY={
 'data':('Data preparation','01',[], 'Validated sales and outlet data; numeric gaps use column medians, following the source notebook. Duplicates removed by outlet and month.'),
 'benchmark':('Outlet benchmarking','01',['data'],'Weighted normalized peer KPIs across the full source period.'),
 'score':('Performance score','01',['benchmark'],'Seven ranked drivers; Excellent ≥80, Good ≥65, Needs Improvement ≥50.'),
 'performance':('Outlet performance agent','01',['score'],'Explainable outlet insights using profit, conversion, satisfaction and complaints.'),
 'forecast':('Demand forecasting','02',[],'Three preceding months, excluding the current month; first three estimates are unavailable. The source column says next month, but the supplied algorithm is a lagged estimate.'),
 'inventory':('Inventory agent','02',[],'Stock, freshness and replenishment rules. Uses the forecast supplied in the inventory workbook.'),
 'staff':('Staff agent','03',[],'Retention and service signals from the supplied staff agent.'),
 'workforce':('Workforce analytics','03',[],'Validated combined workbook: productivity, attendance and scheduling.'),
 'marketing':('Marketing agent','03',['data'],'Marketing spend, revenue efficiency and effectiveness using the team agent.'),
 'campaigns':('Marketing effectiveness','03',[],'Campaign ROI, reach, conversion and engagement from the combined workbook.'),
 'operations':('Operational insights','03',[],'Recent three months versus previous three months; weighted operational risks.'),
 'health':('Cross-functional health','03',['inventory','workforce','campaigns'],'Combines workforce, marketing and latest inventory coverage by Outlet_ID.')}
FILES={'data':P/'milestone1_clean_data.csv','benchmark':E/'benchmarking/benchmark_output.csv','score':E/'performance_score/performance_score_output.csv','performance':P/'outlet_agent_output.csv','forecast':P/'demand_forecast_output.csv','inventory':P/'inventory_agent_output.csv','staff':E/'staff_agent/staff_agent_output.csv','workforce':P/'m3_staff_workforce_output.csv','marketing':P/'marketing_agent_output.csv','campaigns':P/'m3_marketing_effectiveness_output.csv','operations':P/'operational_insights_output.csv','health':P/'m3_operational_insights.csv'}
def script(path):
 r=subprocess.run([sys.executable,str(E/path)],cwd=E,capture_output=True,text=True,timeout=240)
 if r.returncode:raise RuntimeError(r.stderr[-2000:])
def prepared():
 from src.milestone3.data_preparation import load_milestone3_source
 d,q=load_milestone3_source(E/'data/raw/FranchiseOps_AI_Milestone2_Milestone3_Combined_Dataset.xlsx')
 pd.DataFrame([q]).to_csv(P/'m3_data_quality.csv',index=False)
 return d

def execute(key):
 if key=='data':
  columns=pd.read_csv(FILES[key],nrows=0).columns.tolist()
  d=pd.read_excel(E/'data/raw/FranchiseOps_AI_Milestone2_Inventory_Dataset.xlsx',sheet_name='Raw_Outlet_Data',usecols=columns)
  for col in ['Footfall','Orders','Conversion_Rate_%','Average_Order_Value_INR','Marketing_Spend_INR','Employee_Turnover_%','Customer_Satisfaction_1_5','Complaints']:
   d[col]=pd.to_numeric(d[col],errors='coerce');d[col]=d[col].fillna(d[col].median())
  d['Month']=pd.to_datetime(d['Month'],errors='raise').dt.strftime('%Y-%m')
  if d[['Outlet_ID','Month','Sales_Revenue_INR','Orders']].isna().any().any():raise ValueError('Sales source has missing required fields')
  d=d.drop_duplicates(['Outlet_ID','Month']);d.to_csv(FILES[key],index=False)
 elif key=='benchmark':script('benchmarking/benchmarking.py')
 elif key=='score':script('performance_score/performance_score.py')
 elif key=='performance':
  from src.outlet_performance_agent.outlet_agent import analyze_outlet,generate_insights
  d=pd.read_csv(FILES['data']);b=pd.read_csv(FILES['benchmark']).set_index('Outlet_ID');s=pd.read_csv(FILES['score']).set_index('Outlet_ID');rows=[]
  for oid in d.Outlet_ID.unique():
   a=analyze_outlet(d,oid);ins,rec=generate_insights(a,b.loc[oid],s.loc[oid]);a.update(Insight=' '.join(ins),Recommendation=' '.join(rec) or 'Continue monitoring.',Performance_Score=s.loc[oid,'Performance_Score'],Performance_Category=s.loc[oid,'Performance_Category']);rows.append(a)
  pd.DataFrame(rows).to_csv(FILES[key],index=False)
 elif key=='forecast':script('forecasting/demand_forecasting.py')
 elif key=='inventory':script('inventory_agent/inventory_agent/inventory_agent.py')
 elif key=='staff':script('staff_agent/staff_agent.py')
 elif key=='workforce':
  from src.milestone3.staff_workforce import build_staff_workforce_outputs
  d,m=build_staff_workforce_outputs(prepared());d.to_csv(FILES[key],index=False);m.to_csv(P/'m3_staff_monthly_summary.csv',index=False)
 elif key=='marketing':
  from src.marketing_agent.marketing_agent import build_marketing_agent_output
  build_marketing_agent_output(pd.read_csv(FILES['data'])).to_csv(FILES[key],index=False)
 elif key=='campaigns':
  from src.milestone3.marketing_effectiveness import build_marketing_effectiveness_outputs
  d,m=build_marketing_effectiveness_outputs(prepared());d.to_csv(FILES[key],index=False);m.to_csv(P/'m3_marketing_monthly_summary.csv',index=False)
 elif key=='operations':script('recommendations/operational_insights.py')
 elif key=='health':
  from src.milestone3.operational_insights import build_operational_insights
  from src.milestone2_loader import load_inventory_agent_output
  build_operational_insights(pd.read_csv(FILES['workforce']),pd.read_csv(FILES['campaigns']),load_inventory_agent_output(FILES['inventory'])).to_csv(FILES[key],index=False)

def atomic_json(path,obj):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(obj,allow_nan=False,separators=(',',':')),encoding='utf-8');os.replace(tmp,path)
def export():
 sales=pd.read_csv(FILES['data']);lookup=sales.drop_duplicates('Outlet_ID').set_index('Outlet_ID')[['Outlet_Name','Region','City']].to_dict('index');meta={'generated':datetime.now(timezone.utc).isoformat(),'agents':[],'outlets':lookup}
 for key,(name,milestone,deps,method) in REGISTRY.items():
  path=FILES[key]
  if not path.exists():continue
  d=pd.read_csv(path)
  for col in ['Outlet_Name','Region','City']:
   if col not in d and 'Outlet_ID' in d:d[col]=d.Outlet_ID.map(lambda x:lookup.get(x,{}).get(col))
  rows=json.loads(d.to_json(orient='records',date_format='iso'))
  if len(rows)>2500:
   chunks=[]
   for start in range(0,len(rows),2500):
    filename=f'{key}-{start//2500:03}.json'
    atomic_json(OUT/filename,rows[start:start+2500]);chunks.append(filename)
   atomic_json(OUT/f'{key}.json',{'format':'chunked-v1','rows':len(rows),'chunks':chunks})
  else:
   atomic_json(OUT/f'{key}.json',rows)
  meta['agents'].append({'id':key,'name':name,'milestone':milestone,'dependencies':deps,'method':method,'rows':len(d),'source':str(path.relative_to(E)),'updated':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()})
 atomic_json(OUT/'meta.json',meta)
 return meta

def run(key='all'):
 done=[]
 def visit(k):
  if k in done:return
  for dep in REGISTRY[k][2]:visit(dep)
  print('Running',k,flush=True);execute(k);done.append(k)
 if key=='all':
  for k in REGISTRY:visit(k)
 else:
  if key not in REGISTRY:raise ValueError('Unknown agent')
  visit(key)
 export();return done
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'all')
