"""Stateless public sample. No authentication, uploads, private data or durable state."""
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .db import Store
from .knowledge import answer_question
from .model import Model
from .seed import ACCOUNTS, seed_data

app = FastAPI(title='Vaultwise public sample API', docs_url='/api/docs', openapi_url='/api/openapi.json')
Person = Literal['admin@alpha.test', 'analyst@alpha.test', 'viewer@alpha.test', 'admin@beta.test']


class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=4000)


@app.middleware('http')
async def limits(request: Request, call_next):
    if request.method == 'POST':
        size, chunks = 0, []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 20000:
                return JSONResponse({'detail': 'Request too large'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


def sample(persona, question=None):
    # Every request gets a fresh, isolated synthetic corpus, cleaned up on completion.
    # No users of the full authenticated application can be reached from this app.
    with TemporaryDirectory(prefix='vaultwise-demo-') as directory:
        store = Store(Path(directory) / 'sample.db')
        for email, tenant, role in ACCOUNTS:
            store.execute('INSERT INTO users VALUES (?,?,?,?,?)',
                          (email.split('@')[0] + '-' + tenant, email, 'NO-LOGIN', tenant, role))
        seed_data(store)
        user = store.one('SELECT * FROM users WHERE email=?', (persona,))
        if question is not None:
            return answer_question(store, user, question, Model(mode='extractive'))
        return store.all('SELECT id,title,audience,status FROM documents WHERE tenant=? '
                         'AND (audience=? OR audience=? OR ?=?) ORDER BY title',
                         (user['tenant'], 'all', user['role'], user['role'], 'admin'))


@app.get('/api/health')
def health():
    return {'status': 'ok', 'product': 'Vaultwise', 'mode': 'public-synthetic-demo',
            'persistence': False, 'authentication': False, 'model_mode': 'extractive'}


@app.get('/api/demo/documents')
def documents(persona: Person = 'admin@alpha.test'):
    return sample(persona)


@app.post('/api/demo/ask')
def ask(body: Question, persona: Person = 'admin@alpha.test'):
    if not body.question.strip():
        raise HTTPException(422, 'Enter a question')
    return sample(persona, body.question)


frontend = Path(__file__).resolve().parents[1] / 'public'
if frontend.exists():
    app.mount('/', StaticFiles(directory=frontend, html=True), name='frontend')
