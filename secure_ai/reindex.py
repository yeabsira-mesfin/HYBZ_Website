"""Recover queued document ingestion after an interrupted process."""
import os
from .db import Store
from .knowledge import ingest


if __name__ == '__main__':
    store=Store(os.getenv('DATABASE_PATH','data/application.db'))
    rows=store.all('SELECT id FROM documents WHERE status=?',('queued',))
    for row in rows:
        ingest(store,row['id'])
    print(f'Reindexed {len(rows)} queued documents')
