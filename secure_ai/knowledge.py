"""ACL-first lexical retrieval with asynchronous ingestion and source provenance."""
import math
import re
import time
import uuid
from collections import Counter

from .policy import redact, suspicious


def ingest(store, document_id):
    row = store.one('SELECT * FROM documents WHERE id=?', (document_id,))
    if not row:
        return
    body = redact(row['body'])
    paragraphs = [p.strip() for p in body.split('\n') if p.strip()]
    chunks = [paragraph[i:i+700] for paragraph in paragraphs for i in range(0, len(paragraph), 600)]
    with store.connect() as conn:
        # A deletion that races ingestion must not resurrect a document.
        if not conn.execute('SELECT id FROM documents WHERE id=?', (document_id,)).fetchone():
            return
        conn.execute('DELETE FROM chunks WHERE doc_id=?', (document_id,))
        conn.executemany('INSERT INTO chunks VALUES (?,?,?,?)',
                         [(uuid.uuid4().hex, document_id, i, c) for i, c in enumerate(chunks)])
        conn.execute('UPDATE documents SET status=?,body=? WHERE id=?', ('ready', body, document_id))


def add_document(store, user, title, body, audience='all'):
    doc_id = uuid.uuid4().hex
    store.execute('INSERT INTO documents VALUES (?,?,?,?,?,?,?)',
                  (doc_id, user['tenant'], redact(title), redact(body), audience, 'queued', time.time()))
    store.audit(user, 'document.upload', doc_id)
    return doc_id


def authorized_chunks(store, user):
    # Identity comes from the session. Never accept a tenant or role in the request body.
    return store.all(
        'SELECT c.id,c.body,c.position,d.id AS document_id,d.title FROM chunks c '
        'JOIN documents d ON c.doc_id=d.id WHERE d.tenant=? AND d.status=? '
        'AND (d.audience=? OR d.audience=? OR ?=?)',
        (user['tenant'], 'ready', 'all', user['role'], user['role'], 'admin'))


STOP_WORDS = {'the', 'is', 'a', 'an', 'what', 'how', 'for', 'to', 'of', 'and', 'in', 'do', 'does', 'our'}


def terms(text):
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if w not in STOP_WORDS]


def retrieve(store, user, question, top_k=4):
    rows = authorized_chunks(store, user)
    query = set(terms(question))
    corpus = [Counter(terms(r['body'] + ' ' + r['title'])) for r in rows]
    results = []
    quarantined = 0
    for row, counts in zip(rows, corpus):
        if suspicious(row['body']) or suspicious(row['title']):
            quarantined += 1
            continue
        score = sum((1 + math.log(counts[t])) * math.log(1 + len(rows) / (1 + sum(t in c for c in corpus)))
                    for t in query if counts[t])
        if score > 0:
            results.append(dict(row, score=round(score, 4)))
    return sorted(results, key=lambda r: (-r['score'], r['id']))[:top_k], quarantined


def answer_question(store, user, question, model):
    started = time.perf_counter()
    if suspicious(question):
        store.audit(user, 'question', outcome='blocked')
        return {'answer': 'Request flagged by the injection heuristic. Rephrase as a document question.',
                'sources': [], 'mode': model.mode, 'blocked': True, 'latency_ms': 0,
                'input_tokens': None, 'output_tokens': None, 'cost_usd': None, 'quarantined_chunks': 0}
    sources, quarantined = retrieve(store, user, question)
    result = model.generate(redact(question), sources)
    result['answer'] = redact(result['answer'])
    result.update(sources=sources, blocked=False, quarantined_chunks=quarantined,
                  latency_ms=round((time.perf_counter() - started) * 1000, 2), cost_usd=None)
    store.audit(user, 'question', outcome='answered' if sources else 'no_evidence')
    return result
