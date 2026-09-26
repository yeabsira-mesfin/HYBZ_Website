"""Server-owned identities, scrypt passwords, and revocable opaque sessions."""
import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}${digest}'


def verify_password(password, stored):
    salt, expected = stored.split('$', 1)
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)


def digest_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def identity(request: Request):
    token = request.cookies.get('session', '')
    user = request.app.state.store.one(
        'SELECT u.id,u.email,u.tenant,u.role FROM users u JOIN sessions s ON u.id=s.user_id '
        'WHERE s.digest=? AND s.expires>?', (digest_token(token), time.time()))
    if not user:
        raise HTTPException(401, 'Sign in to continue')
    return user


def require_role(user, *roles):
    if user['role'] not in roles:
        raise HTTPException(403, 'Your role does not allow this action')


def start_session(store, user_id):
    token = secrets.token_urlsafe(32)
    store.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
    store.execute('INSERT INTO sessions VALUES (?,?,?)', (digest_token(token), user_id, time.time() + 3600))
    return token
