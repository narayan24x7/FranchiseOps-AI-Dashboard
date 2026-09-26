import pandas as pd
import numpy as np
from pipeline import FILES

def prepare():
 frames={k:pd.read_csv(FILES[k]) for k in ['data','score','workforce','campaigns','health']}
 checks=[]
 def check(name,ok,detail):
  checks.append(dict(Check=name,Status='Passed' if ok else 'Failed',Evidence=str(detail)))
 sales=frames['data'];required=['Outlet_ID','Month','Sales_Revenue_INR','Profit_INR','Orders','Outlet_Name','Region','City']
 check('Required sales columns',set(required)<=set(sales.columns),', '.join(required))
 if checks[-1]['Status']=='Failed': raise ValueError('Missing required sales columns')
 check('Sales keys complete',not sales[['Outlet_ID','Month']].isna().any().any(),len(sales))
 check('Unique outlet / month',not sales.duplicated(['Outlet_ID','Month']).any(),len(sales))
 check('Valid calendar months',pd.to_datetime(sales.Month,errors='coerce').notna().all(),sales.Month.max())
 nums=sales[['Sales_Revenue_INR','Profit_INR','Orders']].apply(pd.to_numeric,errors='coerce')
 check('Finite financial values',np.isfinite(nums.to_numpy()).all(),'Revenue, profit and orders')
 check('Nonnegative revenue and orders',(nums[['Sales_Revenue_INR','Orders']]>=0).all().all(),'Negative profit is retained as an audit signal')
 ids=set(sales.Outlet_ID)
 for key,metric in [('score','Performance_Score'),('workforce','Average_Staff_Performance_Score'),('campaigns','Marketing_Effectiveness_Score'),('health','Inventory_Score')]:
  d=frames[key];v=pd.to_numeric(d[metric],errors='coerce')
  check(key+' outlet coverage',set(d.Outlet_ID)==ids and not d.Outlet_ID.duplicated().any(),f'{len(d)} outlets / {len(ids)} expected')
  check(key+' score range',v.notna().all() and v.between(0,100).all(),metric+' must be finite, 0–100')
 if any(c['Status']=='Failed' for c in checks):raise ValueError('; '.join(c['Check'] for c in checks if c['Status']=='Failed'))
 return frames,checks
