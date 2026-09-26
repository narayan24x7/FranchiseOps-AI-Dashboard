import pandas as pd
WEIGHTS={'Performance':.25,'Workforce':.20,'Marketing':.20,'Inventory':.20,'Audit':.15}
def build(frames,audit_scores):
 s=frames['data'];base=s.drop_duplicates('Outlet_ID')[['Outlet_ID','Outlet_Name','Region','City']].set_index('Outlet_ID')
 for name,key,col in [('Performance','score','Performance_Score'),('Workforce','workforce','Average_Staff_Performance_Score'),('Marketing','campaigns','Marketing_Effectiveness_Score'),('Inventory','health','Inventory_Score')]:base[name]=frames[key].set_index('Outlet_ID')[col]
 base['Audit']=pd.Series(audit_scores);base['Intelligence_Score']=sum(base[k]*w for k,w in WEIGHTS.items()).round(2)
 base['Priority']=base.Intelligence_Score.map(lambda x:'High' if x<60 else 'Medium' if x<75 else 'Monitor')
 base['Primary_Focus']=base[list(WEIGHTS)].idxmin(axis=1)
 actions={'Performance':'Review low-performing financial and service drivers.','Workforce':'Review productivity, attendance and scheduling.','Marketing':'Review campaign efficiency and spending.','Inventory':'Review replenishment and critical SKU coverage.','Audit':'Review open audit findings and their evidence.'}
 base['Recommended_Action']=base.Primary_Focus.map(actions)
 return base.reset_index().sort_values('Intelligence_Score').to_dict('records')
