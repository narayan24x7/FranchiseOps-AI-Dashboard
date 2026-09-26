PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS outlets (outlet_id TEXT PRIMARY KEY,name TEXT NOT NULL,region TEXT,city TEXT);
CREATE TABLE IF NOT EXISTS monthly_sales (outlet_id TEXT REFERENCES outlets(outlet_id),month TEXT,revenue REAL NOT NULL,profit REAL NOT NULL,orders REAL NOT NULL,PRIMARY KEY(outlet_id,month));
CREATE TABLE IF NOT EXISTS snapshots (name TEXT PRIMARY KEY,payload TEXT NOT NULL,updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,target TEXT,status TEXT,started TEXT,finished TEXT,error TEXT);
CREATE TABLE IF NOT EXISTS run_steps (run_id TEXT REFERENCES runs(id),name TEXT,status TEXT,detail TEXT,PRIMARY KEY(run_id,name));
CREATE TABLE IF NOT EXISTS action_state (finding_id TEXT PRIMARY KEY,status TEXT NOT NULL,owner TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',updated TEXT NOT NULL);
