import base64
import hashlib

from flask import current_app
from itsdangerous import URLSafeSerializer


def _serializer():
    raw = current_app.config.get("SECRET_KEY") or current_app.config.get("JWT_SECRET_KEY") or "dev-fallback"
    key = hashlib.sha256(f"project-credentials:{raw}".encode()).digest()
    secret = base64.urlsafe_b64encode(key).decode().rstrip("=")
    return URLSafeSerializer(secret, salt="project-credential-v1")


def encrypt_secret(plain: str) -> str:
    if plain is None:
        return ""
    return _serializer().dumps(str(plain))


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _serializer().loads(token)
    except Exception:
        return ""
