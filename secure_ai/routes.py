import json
import time

import httpx
from fastapi import BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .auth import identity, require_role
from .knowledge import add_document, answer_question, ingest


class Document(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=100_000)
    audience: Literal['all','analyst','admin'] = 'all'


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=4000)


def register(app):
    store = app.state.store

    @app.get('/api/documents')
    def documents(user=Depends(identity)):
        return store.all('SELECT id,title,audience,status,created FROM documents WHERE tenant=? '
                         'AND (audience=? OR audience=? OR ?=?) ORDER BY created DESC',
                         (user['tenant'], 'all', user['role'], user['role'], 'admin'))

    @app.post('/api/documents', status_code=202)
    def upload(body: Document, tasks: BackgroundTasks, user=Depends(identity)):
        require_role(user, 'admin')
        if not store.consume('upload:' + user['id'], 10, 60):
            raise HTTPException(429, 'Upload limit reached')
        if not body.title.strip() or not body.body.strip():
            raise HTTPException(422, 'Title and content must contain text')
        doc_id = add_document(store, user, body.title, body.body, body.audience)
        tasks.add_task(ingest, store, doc_id)
        return {'id': doc_id, 'status': 'queued'}

    @app.delete('/api/documents/{doc_id}')
    def delete(doc_id: str, user=Depends(identity)):
        require_role(user, 'admin')
        if not store.execute('DELETE FROM documents WHERE id=? AND tenant=?', (doc_id, user['tenant'])):
            raise HTTPException(404, 'Document not found')
        store.audit(user, 'document.delete', doc_id)
        return {'deleted': True}

    def respond(body, user):
        if not store.consume('question:' + user['id'], 60, 60):
            raise HTTPException(429, 'Question limit reached')
        if not body.question.strip():
            raise HTTPException(422, 'Question must contain text')
        try:
            return answer_question(store, user, body.question, app.state.model)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            store.audit(user, 'model', outcome='unavailable')
            raise HTTPException(503, 'Local model unavailable; verify Ollama is running') from exc

    @app.post('/api/ask')
    def ask(body: Question, user=Depends(identity)):
        return respond(body, user)

    @app.post('/api/ask/stream')
    def stream(body: Question, user=Depends(identity)):
        # Post-generation SSE delivery, not token-level model streaming.
        result = respond(body, user)
        def events():
            for i in range(0, len(result['answer']), 120):
                yield 'event: delta\ndata: ' + json.dumps({'text': result['answer'][i:i+120]}) + '\n\n'
            yield 'event: done\ndata: ' + json.dumps(result) + '\n\n'
        return StreamingResponse(events(), media_type='text/event-stream')
