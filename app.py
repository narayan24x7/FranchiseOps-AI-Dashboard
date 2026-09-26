from flask import Flask,jsonify,request,send_from_directory
from pathlib import Path
from database.store import connect,snapshot,now,ROOT
from orchestration.orchestrator import start
app=Flask(__name__,static_folder=str(ROOT/'dashboard/static'),static_url_path='')
app.config['MAX_CONTENT_LENGTH']=16384
# One worker: a running record from a previous process means that run was interrupted.
with connect() as c:
 c.execute("UPDATE run_steps SET status='failed',detail='Server restarted during this stage' WHERE status='running'")
 c.execute("UPDATE run_steps SET status='skipped' WHERE status='pending' AND run_id IN (SELECT id FROM runs WHERE status='running')")
 c.execute("UPDATE runs SET status='failed',finished=?,error='Server restarted; start a new run to retry' WHERE status='running'",(now(),))

@app.get('/')
def index():return app.send_static_file('index.html')
@app.get('/api/status')
def status():return jsonify(mode='live',milestone=4)
@app.get('/api/m4/<name>')
def result(name):
 if name not in ['summary','audit','intelligence','validation']:return jsonify(error='Unknown dataset'),404
 data=snapshot(name)
 if data is None:return jsonify(error='Run python scripts/build_milestone4.py first'),503
 if name=='audit':
  with connect() as c:states={r['finding_id']:dict(r) for r in c.execute('SELECT * FROM action_state')}
  for row in data:
   state=states.get(row['Finding_ID'],{});row.update(Status=state.get('status','Open'),Owner=state.get('owner',''),Note=state.get('note',''))
 return jsonify(data)
@app.get('/api/runs')
def runs():
 with connect() as c:
  rows=[dict(r) for r in c.execute('SELECT * FROM runs ORDER BY started DESC LIMIT 30')]
  for row in rows:row['steps']=[dict(s) for s in c.execute('SELECT * FROM run_steps WHERE run_id=? ORDER BY rowid',(row['id'],))]
 return jsonify(rows)
@app.get('/api/jobs/<id>')
def job(id):
 with connect() as c:r=c.execute('SELECT * FROM runs WHERE id=?',(id,)).fetchone()
 return (jsonify(dict(r,agents=['Milestone 4'])),200) if r else (jsonify(error='Unknown run'),404)
@app.post('/api/run/<target>')
def run(target):
 try:return jsonify(job=start(target)),202
 except ValueError as e:return jsonify(error=str(e)),400
 except RuntimeError as e:return jsonify(error=str(e)),409
@app.post('/api/findings/<id>')
def action(id):
 body=request.get_json(silent=True) or {}
 if id not in {r['Finding_ID'] for r in snapshot('audit',[])}:return jsonify(error='Unknown finding'),404
 if body.get('status') not in ['Open','In progress','Resolved']:return jsonify(error='Invalid status'),400
 owner=body.get('owner','');note=body.get('note','')
 if not isinstance(owner,str) or not isinstance(note,str) or len(owner)>120 or len(note)>2000:return jsonify(error='Invalid owner or note'),400
 with connect() as c:c.execute('INSERT OR REPLACE INTO action_state VALUES(?,?,?,?,?)',(id,body['status'],owner,note,now()))
 return jsonify(saved=True)
@app.get('/api/schema')
def schema():
 with connect() as c:return jsonify([dict(r) for r in c.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")])
if __name__=='__main__':
 import os
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8000)))
