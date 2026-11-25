from __future__ import annotations

import keyring

SERVICE_NAME = "student-workbench"
GITHUB_TOKEN_KEY = "github:token"


def key_for(connection_id: str) -> str:
    return f"platform:{connection_id}"


def save_password(connection_id: str, password: str) -> bool:
    try:
        keyring.set_password(SERVICE_NAME, key_for(connection_id), password)
    except Exception:
        return False
    return True


def delete_password(connection_id: str) -> bool:
    try:
        keyring.delete_password(SERVICE_NAME, key_for(connection_id))
    except Exception:
        return False
    return True


def save_github_token(token: str) -> bool:
    try:
        keyring.set_password(SERVICE_NAME, GITHUB_TOKEN_KEY, token)
    except Exception:
        return False
    return True


def load_github_token() -> str | None:
    try:
        value = keyring.get_password(SERVICE_NAME, GITHUB_TOKEN_KEY)
    except Exception:
        return None
    return value or None


def delete_github_token() -> bool:
    try:
        keyring.delete_password(SERVICE_NAME, GITHUB_TOKEN_KEY)
    except Exception:
        return False
    return True
