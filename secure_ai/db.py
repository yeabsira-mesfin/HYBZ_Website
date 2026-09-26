"""Small SQLite store with transactional writes and explicit tenant predicates."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
 tenant TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','analyst','viewer')));
CREATE TABLE IF NOT EXISTS sessions (
 digest TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
 resource TEXT NOT NULL, outcome TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset REAL NOT NULL);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
 audience TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS chunks (
 id TEXT PRIMARY KEY, doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
 position INTEGER NOT NULL, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS records (
 id TEXT PRIMARY KEY, tenant TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS documents_tenant ON documents(tenant, status);
CREATE INDEX IF NOT EXISTS records_tenant ON records(tenant, kind);
CREATE INDEX IF NOT EXISTS audit_tenant ON audit(tenant, created);
"""


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def all(self, sql, values=()):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, values).fetchall()]

    def one(self, sql, values=()):
        rows = self.all(sql, values)
        return rows[0] if rows else None

    def execute(self, sql, values=()):
        with self.connect() as conn:
            return conn.execute(sql, values).rowcount

    def audit(self, user, action, resource='', outcome='allowed'):
        # Never store raw prompts, passwords, model responses, or document bodies.
        self.execute('INSERT INTO audit VALUES (?,?,?,?,?,?,?)',
                     (uuid.uuid4().hex, user['tenant'], user['id'], action, resource, outcome, time.time()))

    def save(self, tenant, kind, body):
        record_id = uuid.uuid4().hex
        self.execute('INSERT INTO records VALUES (?,?,?,?,?)',
                     (record_id, tenant, kind, json.dumps(body), time.time()))
        return record_id

    def record(self, tenant, kind, record_id):
        row = self.one('SELECT * FROM records WHERE id=? AND tenant=? AND kind=?', (record_id, tenant, kind))
        return dict(id=row['id'], **json.loads(row['body'])) if row else None

    def records(self, tenant, kind):
        rows = self.all('SELECT * FROM records WHERE tenant=? AND kind=? ORDER BY created DESC LIMIT 100',
                        (tenant, kind))
        return [dict(id=r['id'], created=r['created'], **json.loads(r['body'])) for r in rows]

    def consume(self, bucket, limit=30, seconds=60):
        now = time.time()
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM limits WHERE reset < ?', (now,))
            row = conn.execute('SELECT count FROM limits WHERE bucket=?', (bucket,)).fetchone()
            if row and row['count'] >= limit:
                return False
            conn.execute('INSERT INTO limits VALUES (?,1,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1',
                         (bucket, now + seconds))
        return True
