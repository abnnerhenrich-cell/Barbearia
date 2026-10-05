"""PostgreSQL em produção. SQLite somente para desenvolvimento local e testes."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

class Database:
    def __init__(self, app):
        self.app = app

    @property
    def postgres(self):
        return bool(self.app.config.get('DATABASE_URL'))

    @contextmanager
    def transaction(self, write=False):
        if self.postgres:
            import psycopg
            from psycopg.rows import dict_row
            conn = psycopg.connect(self.app.config['DATABASE_URL'], row_factory=dict_row, connect_timeout=10, prepare_threshold=None)
        else:
            conn = sqlite3.connect(self.app.config['SQLITE_PATH'], timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')
            if write:
                conn.execute('BEGIN IMMEDIATE')
        try:
            yield Connection(conn, self.postgres)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self):
        schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
        with self.transaction(write=True) as db:
            for statement in schema.split(';'):
                if statement.strip():
                    db.execute(statement)
            if self.postgres:
                db.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
                exists = db.execute("SELECT 1 FROM pg_constraint WHERE conname='bravo_no_overlap' AND conrelid='bookings'::regclass").fetchone()
                if not exists:
                    db.execute("ALTER TABLE bookings ADD CONSTRAINT bravo_no_overlap EXCLUDE USING gist (professional_id WITH =, day WITH =, int4range(start_minute,end_minute,'[)') WITH &&) WHERE (status <> 'cancelled')")

class Connection:
    def __init__(self, conn, postgres):
        self.conn, self.postgres = conn, postgres

    def execute(self, sql, params=()):
        return self.conn.execute(sql.replace('?', '%s') if self.postgres else sql, params)

    def lock(self, professional_id, day):
        if self.postgres:
            self.execute('SELECT pg_advisory_xact_lock(hashtext(?))', (professional_id + ':' + day,))
