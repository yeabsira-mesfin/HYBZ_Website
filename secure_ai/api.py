"""Authenticated API, request budgets, CSRF protection, and same-origin dashboard."""
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .auth import digest_token, hash_password, identity, start_session, verify_password
from .db import Store
from .model import Model
from .product import KIND, NAME, PORT


class Login(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=256)


def create_app(path=None, model=None):
    app = FastAPI(title=NAME, version='2.0.0')
    app.state.store = Store(path or os.getenv('DATABASE_PATH', 'data/application.db'))
    app.state.model = model or Model()
    dummy_hash = hash_password('invalid-account-placeholder')
    origins = {f'http://localhost:{PORT}', f'http://127.0.0.1:{PORT}'}
    if os.getenv('APP_ORIGIN'):
        origins.add(os.environ['APP_ORIGIN'].rstrip('/'))

    @app.middleware('http')
    async def security(request: Request, call_next):
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            if request.headers.get('x-requested-with') != 'secure-ai':
                return JSONResponse({'detail': 'Missing CSRF request header'}, 403)
            origin = request.headers.get('origin')
            if origin and origin not in origins:
                return JSONResponse({'detail': 'Origin is not allowed'}, 403)
            parts, size = [], 0
            async for part in request.stream():
                size += len(part)
                if size > 200_000:
                    return JSONResponse({'detail': 'Request body exceeds 200 KB'}, 413)
                parts.append(part)
            request._body = b''.join(parts)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'product': NAME, 'kind': KIND, 'model_mode': app.state.model.mode}

    @app.post('/api/login')
    def login(body: Login, request: Request, response: Response):
        store = app.state.store
        client = request.client.host if request.client else 'unknown'
        if not store.consume('login-ip:' + client, 20, 60):
            raise HTTPException(429, 'Too many attempts. Try again in one minute.')
        email = body.email.strip().lower()
        if not store.consume('login-user:' + digest_token(email), 10, 60):
            raise HTTPException(429, 'Too many attempts. Try again in one minute.')
        user = store.one('SELECT * FROM users WHERE email=?', (email,))
        valid = verify_password(body.password, user['password'] if user else dummy_hash)
        if not user or not valid:
            raise HTTPException(401, 'Invalid email or password')
        # Revoke the browser's old session before rotation.
        store.execute('DELETE FROM sessions WHERE digest=?', (digest_token(request.cookies.get('session','')),))
        token = start_session(store, user['id'])
        response.set_cookie('session', token, httponly=True, samesite='strict', max_age=3600,
                            secure=os.getenv('COOKIE_SECURE') == 'true', path='/')
        store.audit(user, 'session.login')
        return {k: user[k] for k in ['id','email','tenant','role']}

    @app.post('/api/logout')
    def logout(request: Request, response: Response, user=Depends(identity)):
        app.state.store.execute('DELETE FROM sessions WHERE digest=?',
                                (digest_token(request.cookies.get('session','')),))
        response.delete_cookie('session', path='/')
        return {'signed_out': True}

    @app.get('/api/me')
    def me(user=Depends(identity)):
        return user

    @app.get('/api/audit')
    def audit(user=Depends(identity)):
        store = app.state.store
        if user['role'] == 'admin':
            return store.all('SELECT * FROM audit WHERE tenant=? ORDER BY created DESC LIMIT 100', (user['tenant'],))
        return store.all('SELECT * FROM audit WHERE tenant=? AND actor=? ORDER BY created DESC LIMIT 100',
                         (user['tenant'], user['id']))

    from .routes import register
    register(app)
    dashboard = Path(__file__).resolve().parents[1] / 'dashboard' / 'dist'
    if dashboard.exists():
        app.mount('/assets', StaticFiles(directory=dashboard/'assets'), name='assets')

    @app.get('/')
    def index():
        if (dashboard / 'index.html').exists():
            return FileResponse(dashboard/'index.html')
        return {'product': NAME, 'dashboard': 'Run npm ci && npm run build in dashboard/', 'api': '/docs'}

    return app


app = create_app()
