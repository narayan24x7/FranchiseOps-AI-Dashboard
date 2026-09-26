import hashlib

def build(frames):
 sales=frames['data'];latest=sales[sales.Month==sales.Month.max()].set_index('Outlet_ID')
 workforce=frames['workforce'].set_index('Outlet_ID');campaigns=frames['campaigns'].set_index('Outlet_ID');health=frames['health'].set_index('Outlet_ID')
 findings=[];scores={}
 for oid,r in latest.iterrows():
  rules=[('LOSS','High',float(r.Profit_INR),0,float(r.Profit_INR)<0,'Review pricing, cost of goods and operating expenses.'),
   ('ATTENDANCE','Medium',float(workforce.loc[oid,'Average_Attendance_Rate']),90,float(workforce.loc[oid,'Average_Attendance_Rate'])<90,'Review attendance patterns and staffing cover.'),
   ('CAMPAIGN_ROI','High',float(campaigns.loc[oid,'Average_Campaign_ROI']),0,float(campaigns.loc[oid,'Average_Campaign_ROI'])<0,'Review campaign spend and attribution before renewing campaigns.'),
   ('INVENTORY','High',float(health.loc[oid,'Inventory_Score']),60,float(health.loc[oid,'Inventory_Score'])<60,'Review critical SKUs, replenishment and freshness.'),
   ('SERVICE','Medium',float(r['Customer_Satisfaction_1_5']),3,float(r['Customer_Satisfaction_1_5'])<3,'Investigate customer feedback and service quality.')]
  penalty=0
  for rule,severity,value,threshold,failed,action in rules:
   if not failed:continue
   penalty+=20 if severity=='High' else 10
   findings.append(dict(Finding_ID=hashlib.sha256(f'{oid}:{rule}'.encode()).hexdigest()[:16],Outlet_ID=oid,Outlet_Name=r.Outlet_Name,Region=r.Region,Rule=rule,Severity=severity,Value=round(value,2),Threshold=threshold,Period=str(r.Month) if rule in ['LOSS','SERVICE'] else 'Full-period / latest inventory',Evidence=f'{rule}: {value:.2f} below {threshold}',Recommended_Action=action,Status='Open'))
  scores[oid]=max(0,100-penalty)
 return findings,scores
