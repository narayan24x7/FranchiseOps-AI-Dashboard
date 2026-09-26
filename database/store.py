import os,sqlite3,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def now(): return datetime.now(timezone.utc).isoformat()
def connect():
 p=Path(os.environ.get('FRANCHISEOPS_DATA_DIR',ROOT/'runtime'));p.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(p/'franchiseops.db',timeout=30);c.row_factory=sqlite3.Row
 c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA journal_mode=WAL')
 c.executescript((ROOT/'database/schema.sql').read_text());return c
def snapshot(name,default=None):
 with connect() as c: row=c.execute('SELECT payload FROM snapshots WHERE name=?',(name,)).fetchone()
 return json.loads(row[0]) if row else default
def save(c,name,value):
 c.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?,?)',(name,json.dumps(value,allow_nan=False),now()))
