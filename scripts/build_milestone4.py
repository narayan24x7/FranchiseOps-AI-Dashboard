import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orchestration.orchestrator import start
from database.store import connect
id=start(background=False)
with connect() as c:r=c.execute('SELECT * FROM runs WHERE id=?',(id,)).fetchone()
if r['status']!='succeeded':raise SystemExit(r['error'])
print('Milestone 4 ready:',id)
