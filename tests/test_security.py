import secrets
import time

import pytest
from fastapi.testclient import TestClient

from secure_ai.api import create_app
from secure_ai.auth import digest_token
from secure_ai.model import Model
from secure_ai.seed import seed_data, seed_users


@pytest.fixture
def setup(tmp_path):
    password = secrets.token_urlsafe(20)
    app = create_app(tmp_path/'test.db', Model('extractive'))
    seed_users(app.state.store, password)
    seed_data(app.state.store)
    return app, password


def login(setup, account='admin@alpha.test'):
    app,password=setup
    client=TestClient(app, headers={'X-Requested-With':'secure-ai'})
    response=client.post('/api/login',json={'email':account,'password':password})
    assert response.status_code==200
    return client


def test_requires_authentication(setup):
    assert TestClient(setup[0]).get('/api/me').status_code==401


def test_sessions_revoke_on_logout(setup):
    client=login(setup)
    token=client.cookies['session']
    assert client.post('/api/logout').status_code==200
    assert client.get('/api/me',headers={'Cookie':'session='+token}).status_code==401


def test_expired_session_fails(setup):
    client=login(setup)
    setup[0].state.store.execute('UPDATE sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/me').status_code==401


def test_login_rotates_session(setup):
    client=login(setup)
    old=client.cookies['session']
    client.post('/api/login',json={'email':'admin@alpha.test','password':setup[1]})
    assert old!=client.cookies['session']
    assert not setup[0].state.store.one('SELECT digest FROM sessions WHERE digest=?',(digest_token(old),))


def test_csrf_missing_header_and_foreign_origin(setup):
    client=TestClient(setup[0])
    assert client.post('/api/login',json={}).status_code==403
    assert client.post('/api/login',json={},headers={'X-Requested-With':'secure-ai','Origin':'https://evil.example'}).status_code==403


def test_request_body_limit(setup):
    client=TestClient(setup[0],headers={'X-Requested-With':'secure-ai'})
    assert client.post('/api/login',content='x'*200001).status_code==413


def test_cookies_and_headers(setup):
    client=TestClient(setup[0],headers={'X-Requested-With':'secure-ai'})
    res=client.post('/api/login',json={'email':'admin@alpha.test','password':setup[1]})
    assert 'HttpOnly' in res.headers['set-cookie'] and 'SameSite=strict' in res.headers['set-cookie']
    assert res.headers['x-frame-options']=='DENY'
    assert "frame-ancestors 'none'" in res.headers['content-security-policy']


def test_login_rate_limited(setup):
    client=TestClient(setup[0],headers={'X-Requested-With':'secure-ai'})
    for _ in range(10):
        assert client.post('/api/login',json={'email':'missing@alpha.test','password':'incorrect'}).status_code==401
    assert client.post('/api/login',json={'email':'missing@alpha.test','password':'incorrect'}).status_code==429


def test_audit_does_not_cross_tenants(setup):
    alpha=login(setup)
    beta=login(setup,'admin@beta.test')
    assert all(r['tenant']=='alpha' for r in alpha.get('/api/audit').json())
    assert all(r['tenant']=='beta' for r in beta.get('/api/audit').json())


def test_database_rate_budget_is_atomic(setup):
    from concurrent.futures import ThreadPoolExecutor
    store=setup[0].state.store
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:store.consume('parallel',5,60),range(20)))
    assert sum(results)==5
